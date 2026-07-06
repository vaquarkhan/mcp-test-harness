"""Tests for resiliency assertions and performance baselines."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from mcp_test_harness.assertions import MCPAssertionError
from mcp_test_harness.baselines import (
    assert_latency_within_baseline,
    compare_metric,
    load_baseline,
    save_baseline,
)
from mcp_test_harness.resiliency import (
    assert_degrades_gracefully,
    assert_reconnects,
    assert_survives_crash,
)


@dataclass
class Content:
    text: str = ""
    isError: bool = False


@dataclass
class ToolResult:
    content: list[Content] = field(default_factory=list)


class FakeResSession:
    def __init__(self) -> None:
        self.calls = 0

    async def call_tool(self, name: str, args: dict) -> ToolResult:
        self.calls += 1
        if args.get("__mcp_harness_probe_invalid__") or args.get("__mcp_harness_error_burst__"):
            return ToolResult(content=[Content(text="bad", isError=True)])
        if args.get("bad"):
            return ToolResult(content=[Content(text="invalid", isError=True)])
        return ToolResult(content=[Content(text="ok")])

    async def list_tools(self) -> list:
        return []


@pytest.mark.asyncio
async def test_degrades_gracefully() -> None:
    session = FakeResSession()
    await assert_degrades_gracefully(session, "t", {"bad": True})


@pytest.mark.asyncio
async def test_degrades_gracefully_fails_on_success() -> None:
    session = FakeResSession()
    with pytest.raises(MCPAssertionError, match="without isError"):
        await assert_degrades_gracefully(session, "t", {})


@pytest.mark.asyncio
async def test_reconnects_and_survives() -> None:
    session = FakeResSession()
    await assert_reconnects(session, "t", {})
    await assert_survives_crash(session, "t", {})


def test_baseline_compare(tmp_path: Path) -> None:
    p = tmp_path / "baseline.json"
    save_baseline(p, {"echo_p95": 100.0})
    data = load_baseline(p)
    compare_metric("echo_p95", 105.0, data, max_regression_pct=10.0)
    with pytest.raises(MCPAssertionError, match="regressed"):
        compare_metric("echo_p95", 200.0, data, max_regression_pct=10.0)


@pytest.mark.asyncio
async def test_latency_within_baseline(tmp_path: Path) -> None:
    p = tmp_path / "baseline.json"
    p.write_text(json.dumps({"metrics": {"echo_max": 5000.0}}), encoding="utf-8")
    session = FakeResSession()
    await assert_latency_within_baseline(
        session, "t", {}, p, "echo_max", runs=1, warmup=0, max_regression_pct=50.0
    )
