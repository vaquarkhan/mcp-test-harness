"""Test scheduler for the MCP Test Harness.

Handles sequential and parallel test execution. Sequential mode uses a
single server instance and runs tests one at a time. Parallel mode
distributes tests across multiple workers, each with its own server
instance and transport connection.

Requirements: 13.1, 13.2, 13.3, 13.4, 13.5
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass

from mcp_test_harness.config import HarnessConfig
from mcp_test_harness.discovery import HarnessCase
from mcp_test_harness.executor import CaseExecutor
from mcp_test_harness.fixtures import FixtureManager, FixtureScope, register_builtin_fixtures
from mcp_test_harness.lifecycle import ManagedServer, ServerCrashedError, ServerLifecycleManager
from mcp_test_harness.models import CaseResult, SessionResults, CaseStatus

logger = logging.getLogger(__name__)

# Harness version -- used in SessionResults metadata
_HARNESS_VERSION = "0.1.0"


class HarnessScheduler:
    """Schedule and execute test cases sequentially or in parallel.

    Sequential mode (Req 13.5): starts one server, runs all tests through
    the executor one at a time, then shuts down.

    Parallel mode (Req 13.1, 13.2): creates N workers, each with its own
    server instance. Tests are distributed across workers and executed
    concurrently. Results are aggregated into a single ``SessionResults``.
    """

    async def run_sequential(
        self,
        test_cases: list[HarnessCase],
        config: HarnessConfig,
    ) -> SessionResults:
        """Run tests one at a time with a single server instance.

        Parameters
        ----------
        test_cases:
            The discovered test cases to execute.
        config:
            The harness configuration.

        Returns
        -------
        SessionResults
            Aggregated results for the entire run.
        """
        start_time = time.monotonic()
        results: list[CaseResult] = []
        capabilities: dict = {}
        protocol_version = ""

        lifecycle = ServerLifecycleManager()
        server: ManagedServer | None = None

        try:
            server = await lifecycle.start(config)
            capabilities = server.capabilities
            protocol_version = capabilities.get("protocolVersion", "")
            lifecycle.start_monitor(server)

            executor = CaseExecutor(default_timeout=config.timeout)
            fixtures = FixtureManager()
            register_builtin_fixtures(fixtures)

            for test_case in test_cases:
                try:
                    result = await executor.execute(test_case, server, fixtures)
                except ServerCrashedError as exc:
                    logger.error("Server crashed during test '%s': %s", test_case.name, exc)
                    result = CaseResult(
                        name=test_case.name,
                        module=str(test_case.module_path),
                        status=CaseStatus.ERROR,
                        duration_ms=0.0,
                        error=f"Server crashed: {exc}",
                    )
                    results.append(result)
                    # Mark remaining tests as errored
                    remaining = test_cases[test_cases.index(test_case) + 1 :]
                    for remaining_tc in remaining:
                        results.append(
                            CaseResult(
                                name=remaining_tc.name,
                                module=str(remaining_tc.module_path),
                                status=CaseStatus.ERROR,
                                duration_ms=0.0,
                                error="Server crashed before this test could run",
                            )
                        )
                    break
                else:
                    results.append(result)

                # Teardown per-module fixtures between modules
                if (
                    test_cases.index(test_case) < len(test_cases) - 1
                    and test_case.module_path
                    != test_cases[test_cases.index(test_case) + 1].module_path
                ):
                    await fixtures.teardown(FixtureScope.PER_MODULE)

            # Final per-module teardown
            await fixtures.teardown(FixtureScope.PER_MODULE)

        except Exception as exc:
            logger.error("Failed to start server: %s", exc)
            # Mark all tests as errored
            for tc in test_cases:
                results.append(
                    CaseResult(
                        name=tc.name,
                        module=str(tc.module_path),
                        status=CaseStatus.ERROR,
                        duration_ms=0.0,
                        error=f"Server startup failed: {exc}",
                    )
                )
        finally:
            if server is not None:
                await lifecycle.shutdown(server)

        total_duration_ms = (time.monotonic() - start_time) * 1000.0
        return _aggregate_results(results, total_duration_ms, capabilities, protocol_version)

    async def run_parallel(
        self,
        test_cases: list[HarnessCase],
        config: HarnessConfig,
        workers: int | None = None,
    ) -> SessionResults:
        """Run tests across multiple workers, each with its own server.

        Parameters
        ----------
        test_cases:
            The discovered test cases to execute.
        config:
            The harness configuration.
        workers:
            Number of parallel workers. Defaults to ``os.cpu_count()``.

        Returns
        -------
        SessionResults
            Aggregated results from all workers.
        """
        start_time = time.monotonic()
        worker_count = workers or os.cpu_count() or 1

        if not test_cases:
            total_duration_ms = (time.monotonic() - start_time) * 1000.0
            return _aggregate_results([], total_duration_ms, {}, "")

        # Distribute tests across workers in round-robin fashion
        buckets: list[list[HarnessCase]] = [[] for _ in range(worker_count)]
        for i, tc in enumerate(test_cases):
            buckets[i % worker_count].append(tc)

        # Remove empty buckets (when fewer tests than workers)
        buckets = [b for b in buckets if b]

        # Run all workers concurrently
        worker_tasks = [
            self._run_worker(bucket, config, worker_id=idx)
            for idx, bucket in enumerate(buckets)
        ]
        worker_results = await asyncio.gather(*worker_tasks, return_exceptions=False)

        # Aggregate
        all_results: list[CaseResult] = []
        capabilities: dict = {}
        protocol_version = ""

        for wr in worker_results:
            all_results.extend(wr.results)
            if wr.capabilities:
                capabilities = wr.capabilities
            if wr.protocol_version:
                protocol_version = wr.protocol_version

        total_duration_ms = (time.monotonic() - start_time) * 1000.0
        return _aggregate_results(all_results, total_duration_ms, capabilities, protocol_version)

    # ------------------------------------------------------------------
    # Internal: single worker
    # ------------------------------------------------------------------

    async def _run_worker(
        self,
        test_cases: list[HarnessCase],
        config: HarnessConfig,
        worker_id: int,
    ) -> _WorkerResult:
        """Run a batch of tests on a dedicated server instance.

        If the server crashes, affected tests are marked as errored and
        the worker stops (Req 13.4). Other workers continue independently.
        """
        results: list[CaseResult] = []
        capabilities: dict = {}
        protocol_version = ""

        lifecycle = ServerLifecycleManager()
        server: ManagedServer | None = None

        try:
            server = await lifecycle.start(config)
            capabilities = server.capabilities
            protocol_version = capabilities.get("protocolVersion", "")
            lifecycle.start_monitor(server)

            executor = CaseExecutor(default_timeout=config.timeout)
            fixtures = FixtureManager()
            register_builtin_fixtures(fixtures)

            for test_case in test_cases:
                try:
                    result = await executor.execute(test_case, server, fixtures)
                except ServerCrashedError as exc:
                    logger.error(
                        "Worker %d: server crashed during test '%s': %s",
                        worker_id,
                        test_case.name,
                        exc,
                    )
                    result = CaseResult(
                        name=test_case.name,
                        module=str(test_case.module_path),
                        status=CaseStatus.ERROR,
                        duration_ms=0.0,
                        error=f"Server crashed: {exc}",
                    )
                    results.append(result)
                    # Mark remaining tests in this worker as errored
                    remaining = test_cases[test_cases.index(test_case) + 1 :]
                    for remaining_tc in remaining:
                        results.append(
                            CaseResult(
                                name=remaining_tc.name,
                                module=str(remaining_tc.module_path),
                                status=CaseStatus.ERROR,
                                duration_ms=0.0,
                                error="Server crashed before this test could run",
                            )
                        )
                    break
                else:
                    results.append(result)

            # Teardown per-module fixtures
            await fixtures.teardown(FixtureScope.PER_MODULE)

        except Exception as exc:
            logger.error("Worker %d: failed to start server: %s", worker_id, exc)
            for tc in test_cases:
                results.append(
                    CaseResult(
                        name=tc.name,
                        module=str(tc.module_path),
                        status=CaseStatus.ERROR,
                        duration_ms=0.0,
                        error=f"Worker {worker_id} server startup failed: {exc}",
                    )
                )
        finally:
            if server is not None:
                await lifecycle.shutdown(server)

        return _WorkerResult(
            results=results,
            capabilities=capabilities,
            protocol_version=protocol_version,
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


@dataclass
class _WorkerResult:
    """Internal result from a single parallel worker."""

    results: list[CaseResult]
    capabilities: dict
    protocol_version: str


def _aggregate_results(
    results: list[CaseResult],
    total_duration_ms: float,
    capabilities: dict,
    protocol_version: str,
) -> SessionResults:
    """Build a ``SessionResults`` from a flat list of ``CaseResult``."""
    passed = sum(1 for r in results if r.status == CaseStatus.PASSED)
    failed = sum(1 for r in results if r.status == CaseStatus.FAILED)
    errored = sum(1 for r in results if r.status == CaseStatus.ERROR)
    skipped = sum(1 for r in results if r.status == CaseStatus.SKIPPED)
    timed_out = sum(1 for r in results if r.status == CaseStatus.TIMEOUT)

    return SessionResults(
        test_results=results,
        total_duration_ms=total_duration_ms,
        server_capabilities=capabilities,
        protocol_version=protocol_version,
        harness_version=_HARNESS_VERSION,
        passed=passed,
        failed=failed,
        errored=errored,
        skipped=skipped,
        timed_out=timed_out,
    )
