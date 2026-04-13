"""Unit tests for mcp_test_harness.executor."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from mcp_test_harness.assertions import MCPAssertionError
from mcp_test_harness.discovery import HarnessCase
from mcp_test_harness.executor import CaseExecutor
from mcp_test_harness.fixtures import FixtureManager, FixtureScope
from mcp_test_harness.lifecycle import ManagedServer
from mcp_test_harness.models import CaseStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_server() -> ManagedServer:
    """Create a minimal ManagedServer stub."""
    return ManagedServer(
        process=None,
        session=MagicMock(),
        transport=MagicMock(),
        capabilities={},
    )


def _make_fixtures() -> FixtureManager:
    """Create a FixtureManager with no registered fixtures."""
    return FixtureManager()


def _make_case(
    func,
    *,
    name: str = "test_example",
    markers: dict | None = None,
    is_async: bool | None = None,
) -> HarnessCase:
    """Build a HarnessCase wrapping *func*."""
    import inspect

    return HarnessCase(
        name=name,
        module_path=Path("tests/fake_test.py"),
        func=func,
        markers=markers or {},
        is_async=is_async if is_async is not None else inspect.iscoroutinefunction(func),
    )


# ---------------------------------------------------------------------------
# Tests: basic pass / fail
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sync_passing_test():
    """A sync test function that passes returns PASSED."""
    def my_test():
        pass

    executor = CaseExecutor()
    result = await executor.execute(_make_case(my_test), _make_server(), _make_fixtures())

    assert result.status == CaseStatus.PASSED
    assert result.error is None
    assert result.duration_ms >= 0


@pytest.mark.asyncio
async def test_async_passing_test():
    """An async test function that passes returns PASSED."""
    async def my_test():
        pass

    executor = CaseExecutor()
    result = await executor.execute(_make_case(my_test), _make_server(), _make_fixtures())

    assert result.status == CaseStatus.PASSED
    assert result.error is None


@pytest.mark.asyncio
async def test_assertion_error_marks_failed():
    """A plain AssertionError marks the test as FAILED with traceback."""
    def my_test():
        assert False, "expected failure"

    executor = CaseExecutor()
    result = await executor.execute(_make_case(my_test), _make_server(), _make_fixtures())

    assert result.status == CaseStatus.FAILED
    assert "expected failure" in (result.error or "")
    assert result.traceback is not None


@pytest.mark.asyncio
async def test_mcp_assertion_error_captures_diff():
    """MCPAssertionError captures the diff in assertion_diff."""
    async def my_test():
        raise MCPAssertionError("mismatch", diff="- expected\n+ actual")

    executor = CaseExecutor()
    result = await executor.execute(_make_case(my_test), _make_server(), _make_fixtures())

    assert result.status == CaseStatus.FAILED
    assert result.assertion_diff == "- expected\n+ actual"
    assert "mismatch" in (result.error or "")


@pytest.mark.asyncio
async def test_unhandled_exception_marks_failed():
    """An unhandled exception marks the test as FAILED with traceback."""
    def my_test():
        raise RuntimeError("boom")

    executor = CaseExecutor()
    result = await executor.execute(_make_case(my_test), _make_server(), _make_fixtures())

    assert result.status == CaseStatus.FAILED
    assert "RuntimeError" in (result.error or "")
    assert result.traceback is not None


# ---------------------------------------------------------------------------
# Tests: skip marker
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_skip_marker():
    """A test with skip marker is SKIPPED without execution."""
    call_count = 0

    def my_test():
        nonlocal call_count
        call_count += 1

    case = _make_case(my_test, markers={"skip": True, "reason": "not ready"})
    executor = CaseExecutor()
    result = await executor.execute(case, _make_server(), _make_fixtures())

    assert result.status == CaseStatus.SKIPPED
    assert result.error == "not ready"
    assert call_count == 0


# ---------------------------------------------------------------------------
# Tests: timeout
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_timeout_enforcement():
    """A test exceeding its timeout is marked TIMEOUT."""
    async def my_test():
        await asyncio.sleep(10)

    case = _make_case(my_test, markers={"timeout": 0.05})
    executor = CaseExecutor()
    result = await executor.execute(case, _make_server(), _make_fixtures())

    assert result.status == CaseStatus.TIMEOUT
    assert "timeout" in (result.error or "").lower()


@pytest.mark.asyncio
async def test_default_timeout_used():
    """When no marker timeout, the executor's default_timeout is used."""
    async def my_test():
        await asyncio.sleep(10)

    executor = CaseExecutor(default_timeout=0.05)
    result = await executor.execute(_make_case(my_test), _make_server(), _make_fixtures())

    assert result.status == CaseStatus.TIMEOUT


# ---------------------------------------------------------------------------
# Tests: retry logic
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retry_eventual_pass_is_flaky():
    """A test that fails then passes is marked PASSED + flaky."""
    call_count = 0

    def my_test():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise AssertionError("not yet")

    case = _make_case(my_test, markers={"retry": 3})
    executor = CaseExecutor()
    result = await executor.execute(case, _make_server(), _make_fixtures())

    assert result.status == CaseStatus.PASSED
    assert result.flaky is True
    assert result.retry_count == 2  # 2 retries before passing
    assert len(result.attempt_results) == 3
    assert result.attempt_results[0].status == CaseStatus.FAILED
    assert result.attempt_results[1].status == CaseStatus.FAILED
    assert result.attempt_results[2].status == CaseStatus.PASSED


@pytest.mark.asyncio
async def test_retry_all_fail():
    """A test that fails all retry attempts is marked FAILED."""
    def my_test():
        raise AssertionError("always fails")

    case = _make_case(my_test, markers={"retry": 2})
    executor = CaseExecutor()
    result = await executor.execute(case, _make_server(), _make_fixtures())

    assert result.status == CaseStatus.FAILED
    assert result.flaky is False
    assert result.retry_count == 2
    assert len(result.attempt_results) == 3  # initial + 2 retries


@pytest.mark.asyncio
async def test_no_retry_marker_means_single_attempt():
    """Without retry marker, only one attempt is made."""
    def my_test():
        raise AssertionError("fail")

    executor = CaseExecutor()
    result = await executor.execute(_make_case(my_test), _make_server(), _make_fixtures())

    assert result.status == CaseStatus.FAILED
    assert result.retry_count == 0
    assert len(result.attempt_results) == 1


# ---------------------------------------------------------------------------
# Tests: attempt results tracking
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_attempt_results_have_durations():
    """Each AttemptResult records a positive duration."""
    call_count = 0

    def my_test():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise AssertionError("first fail")

    case = _make_case(my_test, markers={"retry": 1})
    executor = CaseExecutor()
    result = await executor.execute(case, _make_server(), _make_fixtures())

    assert len(result.attempt_results) == 2
    for ar in result.attempt_results:
        assert ar.duration_ms >= 0


# ---------------------------------------------------------------------------
# Tests: fixture injection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fixture_injection():
    """Fixtures are resolved and injected into the test function."""
    received = {}

    def my_test(greeting: str):
        received["greeting"] = greeting

    fm = _make_fixtures()
    fm.register("greeting", lambda: "hello", FixtureScope.PER_TEST)

    executor = CaseExecutor()
    result = await executor.execute(_make_case(my_test), _make_server(), fm)

    assert result.status == CaseStatus.PASSED
    assert received["greeting"] == "hello"


@pytest.mark.asyncio
async def test_fixture_error_marks_error():
    """A fixture resolution failure marks the test as ERROR."""
    def my_test(nonexistent_fixture: str):
        pass

    executor = CaseExecutor()
    result = await executor.execute(_make_case(my_test), _make_server(), _make_fixtures())

    assert result.status == CaseStatus.ERROR
    assert "Fixture error" in (result.error or "")


# ---------------------------------------------------------------------------
# Tests: continues after failure
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_returns_result_on_failure():
    """The executor returns a result (not raises) so the runner can continue."""
    def my_test():
        raise RuntimeError("crash")

    executor = CaseExecutor()
    # Should not raise -- returns a CaseResult
    result = await executor.execute(_make_case(my_test), _make_server(), _make_fixtures())

    assert result.status == CaseStatus.FAILED
    assert result.name == "test_example"
    assert Path(result.module) == Path("tests/fake_test.py")
