"""Close coverage gaps for load helpers (assert_throughput / phases / stateless)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_test_harness.assertions import (
    MCPAssertionError,
    _normalize_load_calls,
    assert_load_phases,
    assert_stateless_throughput,
    assert_throughput,
)
from mcp_test_harness.stateless.throughput import ThroughputMetrics


def test_normalize_load_calls_errors() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        _normalize_load_calls(None, None, [])
    with pytest.raises(ValueError, match="tool"):
        _normalize_load_calls(None, None, [{"arguments": {}}])
    with pytest.raises(ValueError, match="non-dict"):
        _normalize_load_calls(None, None, [{"tool": "t", "arguments": "x"}])
    with pytest.raises(ValueError, match="weight"):
        _normalize_load_calls(None, None, [{"tool": "t", "weight": 0}])
    with pytest.raises(ValueError, match="tool_name is required"):
        _normalize_load_calls("", None, None)
    assert _normalize_load_calls("t", {"a": 1}, None)[0][0] == "t"


def test_throughput_metrics_p95() -> None:
    empty = ThroughputMetrics(
        latencies_s=[], total_requests=0, errors=0, duration_s=0.0
    )
    assert empty.p95_ms == 0.0
    m = ThroughputMetrics(
        latencies_s=[0.01, 0.02, 0.03],
        total_requests=3,
        errors=0,
        duration_s=1.0,
    )
    assert m.p95_ms > 0


@pytest.mark.asyncio
async def test_assert_throughput_duration_and_zero_calls() -> None:
    s = MagicMock()
    s.call_tool = AsyncMock(return_value=MagicMock(isError=False, content=[]))
    with pytest.raises(ValueError, match="duration_s"):
        await assert_throughput(s, "t", duration_s=0)
    with patch(
        "mcp_test_harness.assertions._execute_throughput_burst",
        new_callable=AsyncMock,
        return_value=([], 0, 0.01, 0),
    ):
        with pytest.raises(MCPAssertionError, match="0 calls"):
            await assert_throughput(s, "t", duration_s=0.1)


@pytest.mark.asyncio
async def test_assert_throughput_calls_catalog_and_p90_gate() -> None:
    s = MagicMock()

    async def slow(*_a, **_k):
        await asyncio.sleep(0.02)
        return MagicMock(isError=False, content=[])

    s.call_tool = slow
    await assert_throughput(
        s,
        calls=[
            {"tool": "a", "arguments": {}, "weight": 1},
            {"tool": "b", "weight": 2},
        ],
        concurrent=2,
        total_calls=4,
        max_p90_ms=10_000,
    )
    with pytest.raises(MCPAssertionError, match="p90|Latency"):
        await assert_throughput(s, "t", concurrent=1, total_calls=4, max_p90_ms=0.001)


@pytest.mark.asyncio
async def test_assert_throughput_duration_worker_early_return() -> None:
    s = MagicMock()
    s.call_tool = AsyncMock(return_value=MagicMock(isError=False, content=[]))
    # Very short window + high concurrency exercises the inner time check.
    await assert_throughput(s, "t", concurrent=4, duration_s=0.05, max_error_rate=1.0)


@pytest.mark.asyncio
async def test_assert_load_phases_warmup_and_empty() -> None:
    s = MagicMock()
    s.call_tool = AsyncMock(return_value=MagicMock(isError=False, content=[]))
    await assert_load_phases(
        s,
        "t",
        phases=[
            {"name": "warm", "concurrent": 1, "total_calls": 2, "warmup": True},
            {"name": "meas", "concurrent": 1, "total_calls": 2},
        ],
        max_p99_ms=10_000,
        min_rps=0.0,
    )
    with pytest.raises(ValueError, match="non-empty"):
        await assert_load_phases(s, "t", phases=[])
    with pytest.raises(ValueError, match="concurrent"):
        await assert_load_phases(
            s, "t", phases=[{"name": "bad", "concurrent": 0, "total_calls": 1}]
        )
    with pytest.raises(ValueError, match="duration_s or total_calls"):
        await assert_load_phases(s, "t", phases=[{"name": "bad", "concurrent": 1}])
    with pytest.raises(MCPAssertionError, match="no non-warmup"):
        await assert_load_phases(
            s,
            "t",
            phases=[{"name": "warm", "concurrent": 1, "total_calls": 2, "warmup": True}],
        )


@pytest.mark.asyncio
async def test_assert_throughput_min_rps_fail() -> None:
    s = MagicMock()
    s.call_tool = AsyncMock(return_value=MagicMock(isError=False, content=[]))
    with pytest.raises(MCPAssertionError, match="req/s"):
        await assert_throughput(s, "t", concurrent=1, total_calls=2, min_rps=1_000_000)


@pytest.mark.asyncio
async def test_stateless_throughput_p95_gate() -> None:
    metrics = ThroughputMetrics(
        latencies_s=[0.5], total_requests=1, errors=0, duration_s=1.0
    )
    with patch(
        "mcp_test_harness.stateless.throughput.StatelessThroughputEngine"
    ) as eng_cls:
        eng_cls.return_value.execute_load = AsyncMock(return_value=metrics)
        with pytest.raises(MCPAssertionError, match="p95"):
            await assert_stateless_throughput(
                "http://x",
                "t",
                {},
                duration_s=1,
                max_p95_ms=1.0,
            )
