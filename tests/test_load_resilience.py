"""Load resilience assertion tests."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_test_harness.assertions import MCPAssertionError
from mcp_test_harness.load_resilience import (
    classify_load_failure,
    collect_load_resilience,
    assert_control_engages_under_load,
    assert_fairness_under_load,
    assert_latency_slo_until_shed,
    assert_no_fail_open_under_load,
)


def test_classify_load_failure() -> None:
    assert classify_load_failure(timed_out=True)[0] == "timeout"
    assert classify_load_failure(raised=RuntimeError("RATE_LIMITED"))[1] == "RATE_LIMITED"
    assert classify_load_failure(raised=TimeoutError("x"))[0] == "timeout"
    assert classify_load_failure(raised=Exception("jsonrpc boom"))[0] in {
        "rpc_error",
        "exception",
    }
    assert classify_load_failure(raised=ValueError("nope"))[0] == "exception"
    err = SimpleNamespace(
        isError=True, content=[SimpleNamespace(text="LOAD_SHED please")]
    )
    assert classify_load_failure(result=err)[1] == "LOAD_SHED"
    err2 = SimpleNamespace(isError=True, content=[SimpleNamespace(text="nope")])
    assert classify_load_failure(result=err2)[0] == "tool_error"
    assert classify_load_failure(result=SimpleNamespace(isError=False, content=[]))[0] == "ok"


@pytest.mark.asyncio
async def test_load_asserts() -> None:
    s = MagicMock()

    async def limited(*_a, **_k):
        return SimpleNamespace(
            isError=True, content=[SimpleNamespace(text="CONCURRENCY_LIMIT")]
        )

    s.call_tool = limited
    rep = await assert_control_engages_under_load(
        s,
        "t",
        concurrent=2,
        total_calls=6,
        expect_deny_code="CONCURRENCY_LIMIT",
    )
    assert rep.deny_counts["CONCURRENCY_LIMIT"] >= 1
    with pytest.raises(ValueError):
        await assert_control_engages_under_load(
            s, "t", expect_deny_code="NOT_A_CODE", total_calls=1
        )

    async def always_ok(*_a, **_k):
        return SimpleNamespace(isError=False, content=[])

    s.call_tool = always_ok
    with pytest.raises(MCPAssertionError, match="did not engage"):
        await assert_control_engages_under_load(
            s, "t", concurrent=2, total_calls=4, expect_deny_code="RATE_LIMITED"
        )

    async def rate(*_a, **_k):
        return SimpleNamespace(isError=True, content=[SimpleNamespace(text="RATE_LIMITED")])

    s.call_tool = rate
    with pytest.raises(MCPAssertionError, match="dominant deny"):
        await assert_control_engages_under_load(
            s, "t", concurrent=2, total_calls=4, expect_deny_code="LOAD_SHED"
        )

    # no-fail-open: all ok on stress phase fails
    s.call_tool = always_ok
    with pytest.raises(MCPAssertionError, match="Fail-open"):
        await assert_no_fail_open_under_load(
            s,
            "t",
            phases=[{"name": "stress", "concurrent": 2, "total_calls": 4}],
        )
    with pytest.raises(ValueError):
        await assert_no_fail_open_under_load(s, "t", phases=[])
    with pytest.raises(ValueError):
        await assert_no_fail_open_under_load(
            s, "t", phases=[{"name": "x", "concurrent": 0, "total_calls": 1}]
        )

    s.call_tool = rate
    await assert_no_fail_open_under_load(
        s,
        "t",
        phases=[
            {"name": "warm", "concurrent": 1, "total_calls": 2, "warmup": True},
            {"name": "stress", "concurrent": 2, "total_calls": 4},
        ],
    )

    async def boom(*_a, **_k):
        raise RuntimeError("RATE_LIMITED")

    # exception with deny substring classifies as deny — mislabel check uses error_kind exception + deny
    # Force outcome by patching classify path via raised without code -> exception
    async def crash(*_a, **_k):
        raise RuntimeError("crash")

    s.call_tool = crash
    # control engage will fail (no deny codes)
    with pytest.raises(MCPAssertionError):
        await assert_control_engages_under_load(
            s, "t", concurrent=1, total_calls=2, expect_deny_code="RATE_LIMITED"
        )

    sa = MagicMock()
    sb = MagicMock()
    sa.call_tool = rate
    sb.call_tool = always_ok
    await assert_fairness_under_load(
        sa, sb, tool_name="t", concurrent=2, total_calls=4, max_p99_ms_b=50_000
    )
    sb.call_tool = rate
    with pytest.raises(MCPAssertionError, match="Fairness"):
        await assert_fairness_under_load(
            sa, sb, tool_name="t", concurrent=2, total_calls=4
        )

    s.call_tool = always_ok
    await assert_latency_slo_until_shed(
        s, "t", concurrent=1, total_calls=4, max_p99_ms=50_000
    )
    s.call_tool = rate
    await assert_latency_slo_until_shed(
        s, "t", concurrent=1, total_calls=4, max_p99_ms=1
    )  # no admitted -> pass

    report = await collect_load_resilience(s, "t", concurrent=1, total_calls=2)
    assert report.to_dict()["total"] == 2
