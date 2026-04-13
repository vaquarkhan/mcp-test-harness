"""Tests for the test scheduler (sequential and parallel execution)."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_test_harness.config import HarnessConfig
from mcp_test_harness.discovery import TestCase
from mcp_test_harness.lifecycle import ManagedServer, ServerCrashedError
from mcp_test_harness.models import TestResult, TestStatus
from mcp_test_harness.scheduler import TestScheduler, _aggregate_results


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(**overrides) -> HarnessConfig:
    defaults = dict(server_command="echo hello", transport="stdio", timeout=5.0)
    defaults.update(overrides)
    return HarnessConfig(**defaults)


def _make_test_case(name: str = "test_one", module: str = "test_mod.py") -> TestCase:
    async def _fn():
        pass

    return TestCase(
        name=name,
        module_path=Path(module),
        func=_fn,
        markers={},
        is_async=True,
    )


def _make_managed_server() -> ManagedServer:
    return ManagedServer(
        process=None,
        session=MagicMock(),
        transport=MagicMock(),
        capabilities={"protocolVersion": "2024-11-05"},
    )


def _make_test_result(name: str, status: TestStatus = TestStatus.PASSED) -> TestResult:
    return TestResult(
        name=name,
        module="test_mod.py",
        status=status,
        duration_ms=10.0,
    )


# ---------------------------------------------------------------------------
# _aggregate_results
# ---------------------------------------------------------------------------


class TestAggregateResults:
    def test_empty_results(self):
        run = _aggregate_results([], 100.0, {}, "")
        assert run.passed == 0
        assert run.failed == 0
        assert run.errored == 0
        assert run.skipped == 0
        assert run.timed_out == 0
        assert run.total_duration_ms == 100.0

    def test_counts_statuses(self):
        results = [
            _make_test_result("t1", TestStatus.PASSED),
            _make_test_result("t2", TestStatus.FAILED),
            _make_test_result("t3", TestStatus.ERROR),
            _make_test_result("t4", TestStatus.SKIPPED),
            _make_test_result("t5", TestStatus.TIMEOUT),
            _make_test_result("t6", TestStatus.PASSED),
        ]
        run = _aggregate_results(results, 500.0, {"tools": {}}, "2024-11-05")
        assert run.passed == 2
        assert run.failed == 1
        assert run.errored == 1
        assert run.skipped == 1
        assert run.timed_out == 1
        assert run.protocol_version == "2024-11-05"
        assert run.server_capabilities == {"tools": {}}


# ---------------------------------------------------------------------------
# Sequential execution
# ---------------------------------------------------------------------------


class TestRunSequential:
    @pytest.mark.asyncio
    async def test_runs_all_tests(self):
        """All tests execute and results are aggregated."""
        tc1 = _make_test_case("test_a")
        tc2 = _make_test_case("test_b")
        config = _make_config()
        server = _make_managed_server()

        with (
            patch(
                "mcp_test_harness.scheduler.ServerLifecycleManager"
            ) as MockLCM,
            patch("mcp_test_harness.scheduler.TestExecutor") as MockExec,
            patch("mcp_test_harness.scheduler.FixtureManager") as MockFM,
            patch("mcp_test_harness.scheduler.register_builtin_fixtures"),
        ):
            lcm_instance = MockLCM.return_value
            lcm_instance.start = AsyncMock(return_value=server)
            lcm_instance.shutdown = AsyncMock()
            lcm_instance.start_monitor = MagicMock(return_value=None)

            fm_instance = MockFM.return_value
            fm_instance.teardown = AsyncMock(return_value=[])

            exec_instance = MockExec.return_value
            exec_instance.execute = AsyncMock(
                side_effect=[
                    _make_test_result("test_a", TestStatus.PASSED),
                    _make_test_result("test_b", TestStatus.FAILED),
                ]
            )

            scheduler = TestScheduler()
            run_results = await scheduler.run_sequential([tc1, tc2], config)

        assert run_results.passed == 1
        assert run_results.failed == 1
        assert len(run_results.test_results) == 2
        assert exec_instance.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_server_crash_marks_remaining_errored(self):
        """When the server crashes, remaining tests are marked as errored."""
        tc1 = _make_test_case("test_a")
        tc2 = _make_test_case("test_b")
        tc3 = _make_test_case("test_c")
        config = _make_config()
        server = _make_managed_server()

        with (
            patch(
                "mcp_test_harness.scheduler.ServerLifecycleManager"
            ) as MockLCM,
            patch("mcp_test_harness.scheduler.TestExecutor") as MockExec,
            patch("mcp_test_harness.scheduler.FixtureManager") as MockFM,
            patch("mcp_test_harness.scheduler.register_builtin_fixtures"),
        ):
            lcm_instance = MockLCM.return_value
            lcm_instance.start = AsyncMock(return_value=server)
            lcm_instance.shutdown = AsyncMock()
            lcm_instance.start_monitor = MagicMock(return_value=None)

            fm_instance = MockFM.return_value
            fm_instance.teardown = AsyncMock(return_value=[])

            exec_instance = MockExec.return_value
            exec_instance.execute = AsyncMock(
                side_effect=[
                    _make_test_result("test_a", TestStatus.PASSED),
                    ServerCrashedError("process exited with code 1"),
                ]
            )

            scheduler = TestScheduler()
            run_results = await scheduler.run_sequential([tc1, tc2, tc3], config)

        assert len(run_results.test_results) == 3
        assert run_results.test_results[0].status == TestStatus.PASSED
        assert run_results.test_results[1].status == TestStatus.ERROR
        assert "crashed" in run_results.test_results[1].error.lower()
        assert run_results.test_results[2].status == TestStatus.ERROR

    @pytest.mark.asyncio
    async def test_startup_failure_marks_all_errored(self):
        """When the server fails to start, all tests are errored."""
        tc1 = _make_test_case("test_a")
        tc2 = _make_test_case("test_b")
        config = _make_config()

        with patch(
            "mcp_test_harness.scheduler.ServerLifecycleManager"
        ) as MockLCM:
            lcm_instance = MockLCM.return_value
            lcm_instance.start = AsyncMock(side_effect=RuntimeError("cannot start"))
            lcm_instance.shutdown = AsyncMock()

            scheduler = TestScheduler()
            run_results = await scheduler.run_sequential([tc1, tc2], config)

        assert len(run_results.test_results) == 2
        assert all(r.status == TestStatus.ERROR for r in run_results.test_results)
        assert all("startup failed" in r.error.lower() for r in run_results.test_results)

    @pytest.mark.asyncio
    async def test_empty_test_list(self):
        """Empty test list produces empty results without starting a server."""
        config = _make_config()

        with patch(
            "mcp_test_harness.scheduler.ServerLifecycleManager"
        ) as MockLCM, patch(
            "mcp_test_harness.scheduler.FixtureManager"
        ) as MockFM, patch(
            "mcp_test_harness.scheduler.register_builtin_fixtures"
        ):
            lcm_instance = MockLCM.return_value
            lcm_instance.start = AsyncMock(
                return_value=_make_managed_server()
            )
            lcm_instance.shutdown = AsyncMock()
            lcm_instance.start_monitor = MagicMock(return_value=None)

            fm_instance = MockFM.return_value
            fm_instance.teardown = AsyncMock(return_value=[])

            scheduler = TestScheduler()
            run_results = await scheduler.run_sequential([], config)

        # Server is still started (sequential starts before checking tests)
        assert len(run_results.test_results) == 0
        assert run_results.passed == 0


# ---------------------------------------------------------------------------
# Parallel execution
# ---------------------------------------------------------------------------


class TestRunParallel:
    @pytest.mark.asyncio
    async def test_distributes_across_workers(self):
        """Tests are distributed across workers and results aggregated."""
        test_cases = [_make_test_case(f"test_{i}") for i in range(4)]
        config = _make_config()
        server = _make_managed_server()

        with (
            patch(
                "mcp_test_harness.scheduler.ServerLifecycleManager"
            ) as MockLCM,
            patch("mcp_test_harness.scheduler.TestExecutor") as MockExec,
            patch("mcp_test_harness.scheduler.FixtureManager") as MockFM,
            patch("mcp_test_harness.scheduler.register_builtin_fixtures"),
        ):
            lcm_instance = MockLCM.return_value
            lcm_instance.start = AsyncMock(return_value=server)
            lcm_instance.shutdown = AsyncMock()
            lcm_instance.start_monitor = MagicMock(return_value=None)

            fm_instance = MockFM.return_value
            fm_instance.teardown = AsyncMock(return_value=[])

            exec_instance = MockExec.return_value
            exec_instance.execute = AsyncMock(
                side_effect=lambda tc, srv, fix: _make_test_result(
                    tc.name, TestStatus.PASSED
                )
            )

            scheduler = TestScheduler()
            run_results = await scheduler.run_parallel(test_cases, config, workers=2)

        assert len(run_results.test_results) == 4
        assert run_results.passed == 4
        # Two workers means two server starts
        assert lcm_instance.start.call_count == 2

    @pytest.mark.asyncio
    async def test_worker_crash_does_not_affect_others(self):
        """A crash in one worker doesn't prevent other workers from completing."""
        tc1 = _make_test_case("test_a", module="mod_a.py")
        tc2 = _make_test_case("test_b", module="mod_b.py")
        config = _make_config()
        server = _make_managed_server()

        call_count = 0

        async def mock_execute(tc, srv, fix):
            nonlocal call_count
            call_count += 1
            if tc.name == "test_a":
                raise ServerCrashedError("boom")
            return _make_test_result(tc.name, TestStatus.PASSED)

        with (
            patch(
                "mcp_test_harness.scheduler.ServerLifecycleManager"
            ) as MockLCM,
            patch("mcp_test_harness.scheduler.TestExecutor") as MockExec,
            patch("mcp_test_harness.scheduler.FixtureManager") as MockFM,
            patch("mcp_test_harness.scheduler.register_builtin_fixtures"),
        ):
            lcm_instance = MockLCM.return_value
            lcm_instance.start = AsyncMock(return_value=server)
            lcm_instance.shutdown = AsyncMock()
            lcm_instance.start_monitor = MagicMock(return_value=None)

            fm_instance = MockFM.return_value
            fm_instance.teardown = AsyncMock(return_value=[])

            exec_instance = MockExec.return_value
            exec_instance.execute = AsyncMock(side_effect=mock_execute)

            scheduler = TestScheduler()
            run_results = await scheduler.run_parallel([tc1, tc2], config, workers=2)

        assert len(run_results.test_results) == 2
        # test_a errored from crash, test_b passed on the other worker
        statuses = {r.name: r.status for r in run_results.test_results}
        assert statuses["test_a"] == TestStatus.ERROR
        assert statuses["test_b"] == TestStatus.PASSED

    @pytest.mark.asyncio
    async def test_default_worker_count(self):
        """When workers is None, defaults to os.cpu_count()."""
        config = _make_config()

        with patch("mcp_test_harness.scheduler.os.cpu_count", return_value=4):
            scheduler = TestScheduler()
            # With no tests, just verify it doesn't crash
            run_results = await scheduler.run_parallel([], config, workers=None)

        assert run_results.passed == 0
        assert len(run_results.test_results) == 0

    @pytest.mark.asyncio
    async def test_empty_test_list_parallel(self):
        """Empty test list returns empty results without starting workers."""
        config = _make_config()
        scheduler = TestScheduler()
        run_results = await scheduler.run_parallel([], config, workers=2)
        assert len(run_results.test_results) == 0

    @pytest.mark.asyncio
    async def test_more_workers_than_tests(self):
        """When there are fewer tests than workers, only needed workers run."""
        tc1 = _make_test_case("test_only")
        config = _make_config()
        server = _make_managed_server()

        with (
            patch(
                "mcp_test_harness.scheduler.ServerLifecycleManager"
            ) as MockLCM,
            patch("mcp_test_harness.scheduler.TestExecutor") as MockExec,
            patch("mcp_test_harness.scheduler.FixtureManager") as MockFM,
            patch("mcp_test_harness.scheduler.register_builtin_fixtures"),
        ):
            lcm_instance = MockLCM.return_value
            lcm_instance.start = AsyncMock(return_value=server)
            lcm_instance.shutdown = AsyncMock()
            lcm_instance.start_monitor = MagicMock(return_value=None)

            fm_instance = MockFM.return_value
            fm_instance.teardown = AsyncMock(return_value=[])

            exec_instance = MockExec.return_value
            exec_instance.execute = AsyncMock(
                return_value=_make_test_result("test_only", TestStatus.PASSED)
            )

            scheduler = TestScheduler()
            run_results = await scheduler.run_parallel([tc1], config, workers=8)

        assert len(run_results.test_results) == 1
        assert run_results.passed == 1
        # Only 1 worker should have been started (1 test, 1 bucket)
        assert lcm_instance.start.call_count == 1
