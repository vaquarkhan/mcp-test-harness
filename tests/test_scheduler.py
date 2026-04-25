"""Tests for the test scheduler (sequential and parallel execution)."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_test_harness.config import HarnessConfig
from mcp_test_harness.discovery import HarnessCase
from mcp_test_harness.lifecycle import ManagedServer, ServerCrashedError
from mcp_test_harness.models import CaseResult, CaseStatus
from mcp_test_harness.scheduler import (
    HarnessScheduler,
    _aggregate_results,
    _assert_mcp_compliance,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(**overrides) -> HarnessConfig:
    # Mocks do not provide a real MCP initialize / list_tools — disable
    # post-connect protocol checks for unit tests.
    defaults = dict(
        server_command="echo hello",
        transport="stdio",
        timeout=5.0,
        schema_validation=False,
    )
    defaults.update(overrides)
    return HarnessConfig(**defaults)


def _make_test_case(name: str = "test_one", module: str = "test_mod.py") -> HarnessCase:
    async def _fn():
        pass

    return HarnessCase(
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
        init_result=None,
    )


def _make_test_result(name: str, status: CaseStatus = CaseStatus.PASSED) -> CaseResult:
    return CaseResult(
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
            _make_test_result("t1", CaseStatus.PASSED),
            _make_test_result("t2", CaseStatus.FAILED),
            _make_test_result("t3", CaseStatus.ERROR),
            _make_test_result("t4", CaseStatus.SKIPPED),
            _make_test_result("t5", CaseStatus.TIMEOUT),
            _make_test_result("t6", CaseStatus.PASSED),
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
            patch("mcp_test_harness.scheduler.CaseExecutor") as MockExec,
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
                    _make_test_result("test_a", CaseStatus.PASSED),
                    _make_test_result("test_b", CaseStatus.FAILED),
                ]
            )

            scheduler = HarnessScheduler()
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
            patch("mcp_test_harness.scheduler.CaseExecutor") as MockExec,
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
                    _make_test_result("test_a", CaseStatus.PASSED),
                    ServerCrashedError("process exited with code 1"),
                ]
            )

            scheduler = HarnessScheduler()
            run_results = await scheduler.run_sequential([tc1, tc2, tc3], config)

        assert len(run_results.test_results) == 3
        assert run_results.test_results[0].status == CaseStatus.PASSED
        assert run_results.test_results[1].status == CaseStatus.ERROR
        assert "crashed" in run_results.test_results[1].error.lower()
        assert run_results.test_results[2].status == CaseStatus.ERROR

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

            scheduler = HarnessScheduler()
            run_results = await scheduler.run_sequential([tc1, tc2], config)

        assert len(run_results.test_results) == 2
        assert all(r.status == CaseStatus.ERROR for r in run_results.test_results)
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

            scheduler = HarnessScheduler()
            run_results = await scheduler.run_sequential([], config)

        # Server is still started (sequential starts before checking tests)
        assert len(run_results.test_results) == 0
        assert run_results.passed == 0

    @pytest.mark.asyncio
    async def test_plugin_registry_fixtures_are_registered(self):
        tc1 = _make_test_case("test_a")
        config = _make_config()
        server = _make_managed_server()
        plugin_registry = MagicMock()

        with (
            patch("mcp_test_harness.scheduler.ServerLifecycleManager") as MockLCM,
            patch("mcp_test_harness.scheduler.CaseExecutor") as MockExec,
            patch("mcp_test_harness.scheduler.FixtureManager") as MockFM,
            patch("mcp_test_harness.scheduler.register_builtin_fixtures"),
            patch("mcp_test_harness.scheduler.register_decorated_fixtures"),
        ):
            lcm_instance = MockLCM.return_value
            lcm_instance.start = AsyncMock(return_value=server)
            lcm_instance.shutdown = AsyncMock()
            lcm_instance.start_monitor = MagicMock(return_value=None)
            MockFM.return_value.teardown = AsyncMock(return_value=[])
            MockExec.return_value.execute = AsyncMock(
                return_value=_make_test_result("test_a", CaseStatus.PASSED)
            )
            scheduler = HarnessScheduler()
            await scheduler.run_sequential([tc1], config, plugin_registry=plugin_registry)

        plugin_registry.register_fixtures.assert_called_once()


# ---------------------------------------------------------------------------
# Parallel execution
# ---------------------------------------------------------------------------


class TestRunParallel:
    @pytest.mark.asyncio
    async def test_distributes_across_workers(self):
        """Tests are distributed across workers and results aggregated."""
        # One module per test so round-robin assigns work to multiple workers.
        test_cases = [
            _make_test_case(f"test_{i}", module=f"mod_{i}.py") for i in range(4)
        ]
        config = _make_config()
        server = _make_managed_server()

        with (
            patch(
                "mcp_test_harness.scheduler.ServerLifecycleManager"
            ) as MockLCM,
            patch("mcp_test_harness.scheduler.CaseExecutor") as MockExec,
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
                    tc.name, CaseStatus.PASSED
                )
            )

            scheduler = HarnessScheduler()
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
            return _make_test_result(tc.name, CaseStatus.PASSED)

        with (
            patch(
                "mcp_test_harness.scheduler.ServerLifecycleManager"
            ) as MockLCM,
            patch("mcp_test_harness.scheduler.CaseExecutor") as MockExec,
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

            scheduler = HarnessScheduler()
            run_results = await scheduler.run_parallel([tc1, tc2], config, workers=2)

        assert len(run_results.test_results) == 2
        # test_a errored from crash, test_b passed on the other worker
        statuses = {r.name: r.status for r in run_results.test_results}
        assert statuses["test_a"] == CaseStatus.ERROR
        assert statuses["test_b"] == CaseStatus.PASSED

    @pytest.mark.asyncio
    async def test_default_worker_count(self):
        """When workers is None, defaults to os.cpu_count()."""
        config = _make_config()

        with patch("mcp_test_harness.scheduler.os.cpu_count", return_value=4):
            scheduler = HarnessScheduler()
            # With no tests, just verify it doesn't crash
            run_results = await scheduler.run_parallel([], config, workers=None)

        assert run_results.passed == 0
        assert len(run_results.test_results) == 0

    @pytest.mark.asyncio
    async def test_empty_test_list_parallel(self):
        """Empty test list returns empty results without starting workers."""
        config = _make_config()
        scheduler = HarnessScheduler()
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
            patch("mcp_test_harness.scheduler.CaseExecutor") as MockExec,
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
                return_value=_make_test_result("test_only", CaseStatus.PASSED)
            )

            scheduler = HarnessScheduler()
            run_results = await scheduler.run_parallel([tc1], config, workers=8)

        assert len(run_results.test_results) == 1
        assert run_results.passed == 1
        # Only 1 worker should have been started (1 test, 1 bucket)
        assert lcm_instance.start.call_count == 1

    @pytest.mark.asyncio
    async def test_plugin_registry_fixtures_are_registered_per_worker(self):
        tc1 = _make_test_case("test_only")
        config = _make_config()
        server = _make_managed_server()
        plugin_registry = MagicMock()

        with (
            patch("mcp_test_harness.scheduler.ServerLifecycleManager") as MockLCM,
            patch("mcp_test_harness.scheduler.CaseExecutor") as MockExec,
            patch("mcp_test_harness.scheduler.FixtureManager") as MockFM,
            patch("mcp_test_harness.scheduler.register_builtin_fixtures"),
            patch("mcp_test_harness.scheduler.register_decorated_fixtures"),
        ):
            lcm_instance = MockLCM.return_value
            lcm_instance.start = AsyncMock(return_value=server)
            lcm_instance.shutdown = AsyncMock()
            lcm_instance.start_monitor = MagicMock(return_value=None)
            MockFM.return_value.teardown = AsyncMock(return_value=[])
            MockExec.return_value.execute = AsyncMock(
                return_value=_make_test_result("test_only", CaseStatus.PASSED)
            )
            scheduler = HarnessScheduler()
            await scheduler.run_parallel([tc1], config, workers=1, plugin_registry=plugin_registry)

        plugin_registry.register_fixtures.assert_called_once()


# ---------------------------------------------------------------------------
# Test ordering by marker(order=N)
# ---------------------------------------------------------------------------


class TestOrderMarker:
    @pytest.mark.asyncio
    async def test_sequential_respects_order(self):
        """Tests with order markers run in ascending order."""
        tc_a = _make_test_case("test_a")
        tc_a.markers = {"order": 3}
        tc_b = _make_test_case("test_b")
        tc_b.markers = {"order": 1}
        tc_c = _make_test_case("test_c")
        tc_c.markers = {"order": 2}

        config = _make_config()
        server = _make_managed_server()

        execution_order: list[str] = []

        async def mock_execute(tc, srv, fix):
            execution_order.append(tc.name)
            return _make_test_result(tc.name, CaseStatus.PASSED)

        with (
            patch("mcp_test_harness.scheduler.ServerLifecycleManager") as MockLCM,
            patch("mcp_test_harness.scheduler.CaseExecutor") as MockExec,
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

            scheduler = HarnessScheduler()
            await scheduler.run_sequential([tc_a, tc_b, tc_c], config)

        assert execution_order == ["test_b", "test_c", "test_a"]

    @pytest.mark.asyncio
    async def test_default_order_is_zero(self):
        """Tests without order marker default to 0 and run before higher orders."""
        tc_no_order = _make_test_case("test_no_order")
        tc_no_order.markers = {}
        tc_high = _make_test_case("test_high")
        tc_high.markers = {"order": 10}

        config = _make_config()
        server = _make_managed_server()

        execution_order: list[str] = []

        async def mock_execute(tc, srv, fix):
            execution_order.append(tc.name)
            return _make_test_result(tc.name, CaseStatus.PASSED)

        with (
            patch("mcp_test_harness.scheduler.ServerLifecycleManager") as MockLCM,
            patch("mcp_test_harness.scheduler.CaseExecutor") as MockExec,
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

            scheduler = HarnessScheduler()
            await scheduler.run_sequential([tc_high, tc_no_order], config)

        assert execution_order == ["test_no_order", "test_high"]


# ---------------------------------------------------------------------------
# Parallel: whole-module placement (per-module fixture safety)
# ---------------------------------------------------------------------------


class TestParallelModuleGrouping:
    @pytest.mark.asyncio
    async def test_one_module_uses_one_worker_even_if_more_available(self) -> None:
        """A single test module is never split; extra workers are unused."""
        t1 = _make_test_case("test_a", module="shared_mod.py")
        t2 = _make_test_case("test_b", module="shared_mod.py")
        config = _make_config()
        server = _make_managed_server()

        with (
            patch("mcp_test_harness.scheduler.ServerLifecycleManager") as MockLCM,
            patch("mcp_test_harness.scheduler.CaseExecutor") as MockExec,
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
                return_value=_make_test_result("x", CaseStatus.PASSED)
            )

            scheduler = HarnessScheduler()
            await scheduler.run_parallel([t1, t2], config, workers=4)

        assert lcm_instance.start.call_count == 1
        assert exec_instance.execute.call_count == 2


class TestAssertMcpCompliance:
    @pytest.mark.asyncio
    async def test_parallel_nonzero_worker_skips_post_connect_validation(self) -> None:
        with patch(
            "mcp_test_harness.scheduler.validate_mcp_server_after_connect",
            new_callable=AsyncMock,
        ) as val:
            cfg = _make_config(
                schema_validation=True,
                parallel=True,
                validate_schema_each_parallel_worker=False,
            )
            await _assert_mcp_compliance(cfg, _make_managed_server(), worker_id=1)
        val.assert_not_called()
