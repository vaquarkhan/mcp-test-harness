"""Tests for coverage tracking and unified reporting."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from mcp_test_harness.coverage import (
    CoverageState,
    capture_advertised_inventory,
    coverage_to_dict,
    get_coverage,
    merge_states,
    record_auth_test,
    record_tool_call,
)
from mcp_test_harness.models import CaseResult, CaseStatus, SessionResults
from mcp_test_harness.unified_report import build_unified_summary


@dataclass
class FakeTool:
    name: str


@dataclass
class FakeListTools:
    tools: list[FakeTool] = field(default_factory=list)


class FakeCovSession:
    def __init__(self) -> None:
        self.tools = [FakeTool("echo"), FakeTool("search")]

    async def list_tools(self) -> FakeListTools:
        return FakeListTools(tools=self.tools)

    async def list_resources(self) -> Any:
        return []

    async def list_prompts(self) -> Any:
        return []


@pytest.mark.asyncio
async def test_capture_advertised_and_gaps() -> None:
    session = FakeCovSession()
    await capture_advertised_inventory(session)
    record_tool_call(session, "echo")
    record_auth_test(session, "echo")
    d = coverage_to_dict(get_coverage(session))
    assert d["summary"]["tools_advertised"] == 2
    assert d["summary"]["tools_tested"] == 1
    assert d["gaps"]["untested_tools"] == ["search"]
    assert d["gaps"]["tools_missing_auth_tests"] == []


def test_merge_states() -> None:
    a = CoverageState(advertised_tools={"a"}, tested_tools={"a"})
    b = CoverageState(advertised_tools={"b"}, tested_tools={"b"})
    merged = merge_states(a, b)
    assert merged.advertised_tools == {"a", "b"}
    assert merged.tested_tools == {"a", "b"}


def test_unified_summary_by_tags() -> None:
    results = SessionResults(
        test_results=[
            CaseResult("t1", "m", CaseStatus.PASSED, 1.0, tags=["security"]),
            CaseResult("t2", "m", CaseStatus.FAILED, 1.0, tags=["perf"]),
            CaseResult("t3", "m", CaseStatus.PASSED, 1.0, tags=[]),
        ],
        total_duration_ms=3.0,
        server_capabilities={},
        protocol_version="",
        harness_version="1.1.0",
        passed=2,
        failed=1,
    )
    cov = coverage_to_dict(
        CoverageState(advertised_tools={"echo"}, tested_tools=set())
    )
    summary = build_unified_summary(results, cov)
    assert summary["categories"]["security"]["passed"] == 1
    assert summary["categories"]["performance"]["failed"] == 1
    assert summary["categories"]["functional"]["passed"] == 1
    assert "coverage_headline" in summary
