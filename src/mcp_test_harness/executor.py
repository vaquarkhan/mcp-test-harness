"""Test executor for the MCP Test Harness.

Runs individual test cases with fixture injection, timeout enforcement,
and retry logic.  Captures unhandled exceptions, tracebacks, and
assertion diffs.

Requirements: 2.4, 2.5, 2.6, 14.1, 14.2, 14.3, 14.4
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import time
import traceback
from dataclasses import dataclass, field

from mcp_test_harness.assertions import MCPAssertionError
from mcp_test_harness.discovery import TestCase
from mcp_test_harness.fixtures import FixtureError, FixtureManager, FixtureScope
from mcp_test_harness.lifecycle import ManagedServer
from mcp_test_harness.models import AttemptResult, TestResult, TestStatus

logger = logging.getLogger(__name__)

# Default per-test timeout in seconds (matches CLI default from Req 7.8)
_DEFAULT_TIMEOUT = 30.0


class TestExecutor:
    """Execute individual test cases with timeout and retry handling.

    The executor resolves fixtures via :class:`FixtureManager`, calls the
    test function, enforces per-test timeouts, and implements retry logic
    for tests decorated with the ``retry`` marker.
    """

    def __init__(self, default_timeout: float = _DEFAULT_TIMEOUT) -> None:
        self._default_timeout = default_timeout

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def execute(
        self,
        test_case: TestCase,
        server: ManagedServer,
        fixtures: FixtureManager,
    ) -> TestResult:
        """Execute a single test case and return its result.

        Parameters
        ----------
        test_case:
            The discovered test case to run.
        server:
            The managed MCP server providing the client session.
        fixtures:
            The fixture manager used to resolve test function parameters.

        Returns
        -------
        TestResult
            The outcome including status, duration, error info, and retry
            history.
        """
        # Check for skip marker first (Req 2.7 -- skipped tests)
        if test_case.markers.get("skip"):
            reason = test_case.markers.get("reason", "")
            return TestResult(
                name=test_case.name,
                module=str(test_case.module_path),
                status=TestStatus.SKIPPED,
                duration_ms=0.0,
                error=reason or None,
            )

        # Determine timeout: marker > CLI default
        timeout = test_case.markers.get("timeout", self._default_timeout)

        # Determine retry count from marker (0 means no retries)
        max_retries: int = test_case.markers.get("retry", 0)

        # Inject the managed server so built-in fixtures can access it
        fixtures.set_injected("managed_server", server)

        attempt_results: list[AttemptResult] = []
        total_start = time.monotonic()
        last_result: _AttemptOutcome | None = None

        for attempt_num in range(1, max_retries + 2):  # +2: 1-indexed, includes initial run
            outcome = await self._run_once(
                test_case=test_case,
                fixtures=fixtures,
                timeout=timeout,
                attempt=attempt_num,
            )
            last_result = outcome

            attempt_results.append(
                AttemptResult(
                    attempt=attempt_num,
                    status=outcome.status,
                    duration_ms=outcome.duration_ms,
                    error=outcome.error,
                )
            )

            # If passed, stop retrying
            if outcome.status == TestStatus.PASSED:
                break

            # If not retryable (e.g. ERROR from fixture failure), stop
            if outcome.status == TestStatus.ERROR:
                break

            # For FAILED / TIMEOUT -- retry if attempts remain
            if attempt_num > max_retries:
                break

            logger.info(
                "Test '%s' failed (attempt %d/%d), retrying...",
                test_case.name,
                attempt_num,
                max_retries + 1,
            )

        assert last_result is not None

        total_duration_ms = (time.monotonic() - total_start) * 1000.0

        # Determine flaky: passed after at least one prior failure (Req 14.4)
        flaky = (
            last_result.status == TestStatus.PASSED
            and len(attempt_results) > 1
            and any(a.status != TestStatus.PASSED for a in attempt_results[:-1])
        )

        if flaky:
            logger.warning("Test '%s' is flaky -- passed after retry", test_case.name)

        return TestResult(
            name=test_case.name,
            module=str(test_case.module_path),
            status=last_result.status,
            duration_ms=total_duration_ms,
            error=last_result.error,
            traceback=last_result.tb,
            assertion_diff=last_result.assertion_diff,
            retry_count=len(attempt_results) - 1,
            attempt_results=attempt_results,
            flaky=flaky,
        )

    # ------------------------------------------------------------------
    # Internal: single attempt
    # ------------------------------------------------------------------

    async def _run_once(
        self,
        test_case: TestCase,
        fixtures: FixtureManager,
        timeout: float,
        attempt: int,
    ) -> _AttemptOutcome:
        """Run the test function once, returning the outcome."""
        start = time.monotonic()

        # 1. Resolve fixtures
        try:
            resolved = await fixtures.resolve(test_case.func)
        except FixtureError as exc:
            duration_ms = (time.monotonic() - start) * 1000.0
            return _AttemptOutcome(
                status=TestStatus.ERROR,
                duration_ms=duration_ms,
                error=f"Fixture error: {exc}",
                tb=traceback.format_exc(),
            )

        # 2. Execute the test function with timeout
        try:
            await asyncio.wait_for(
                self._invoke(test_case.func, resolved),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            duration_ms = (time.monotonic() - start) * 1000.0
            return _AttemptOutcome(
                status=TestStatus.TIMEOUT,
                duration_ms=duration_ms,
                error=f"Test exceeded {timeout}s timeout",
            )
        except MCPAssertionError as exc:
            duration_ms = (time.monotonic() - start) * 1000.0
            return _AttemptOutcome(
                status=TestStatus.FAILED,
                duration_ms=duration_ms,
                error=str(exc),
                tb=traceback.format_exc(),
                assertion_diff=exc.diff,
            )
        except AssertionError as exc:
            duration_ms = (time.monotonic() - start) * 1000.0
            return _AttemptOutcome(
                status=TestStatus.FAILED,
                duration_ms=duration_ms,
                error=str(exc),
                tb=traceback.format_exc(),
            )
        except Exception as exc:  # noqa: BLE001
            duration_ms = (time.monotonic() - start) * 1000.0
            return _AttemptOutcome(
                status=TestStatus.FAILED,
                duration_ms=duration_ms,
                error=f"{type(exc).__name__}: {exc}",
                tb=traceback.format_exc(),
            )
        finally:
            # Teardown per-test fixtures after each attempt
            teardown_errors = await fixtures.teardown(FixtureScope.PER_TEST)
            for err in teardown_errors:
                logger.warning(
                    "Fixture teardown error in test '%s': %s",
                    test_case.name,
                    err,
                )

        duration_ms = (time.monotonic() - start) * 1000.0
        return _AttemptOutcome(
            status=TestStatus.PASSED,
            duration_ms=duration_ms,
        )

    # ------------------------------------------------------------------
    # Internal: invoke test function (sync or async)
    # ------------------------------------------------------------------

    @staticmethod
    async def _invoke(func: callable, kwargs: dict) -> None:
        """Call the test function, handling both sync and async."""
        if inspect.iscoroutinefunction(func):
            await func(**kwargs)
        else:
            func(**kwargs)


# ---------------------------------------------------------------------------
# Internal outcome dataclass
# ---------------------------------------------------------------------------


@dataclass
class _AttemptOutcome:
    """Internal result of a single test attempt."""

    status: TestStatus
    duration_ms: float
    error: str | None = None
    tb: str | None = None
    assertion_diff: str | None = None
