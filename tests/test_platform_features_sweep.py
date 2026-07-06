"""Coverage sweep for platform features (coverage, security, resiliency, portal)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from mcp_test_harness.assertions import MCPAssertionError
from mcp_test_harness.baselines import (
    compare_metric,
    load_baseline,
    save_baseline,
)
from mcp_test_harness.coverage import (
    capture_advertised_inventory,
    get_coverage,
    record_prompt,
    record_resource_read,
)
from mcp_test_harness.html_reporter import HTMLReporter
from mcp_test_harness.models import CaseResult, CaseStatus, SessionResults
from mcp_test_harness.reporting import JSONReporter
from mcp_test_harness.resiliency import assert_reconnects, assert_survives_crash
from mcp_test_harness.security_payloads import (
    assert_injection_blocked,
    assert_path_traversal_blocked,
    run_security_payload_pack,
)
from mcp_test_harness.unified_report import build_unified_summary


@dataclass
class Content:
    text: str = ""
    isError: bool = False


@dataclass
class ToolResult:
    content: list[Content] = field(default_factory=list)


class ExplodingSession:
    async def list_tools(self) -> Any:
        raise RuntimeError("boom")

    async def list_resources(self) -> Any:
        raise RuntimeError("boom")

    async def list_prompts(self) -> Any:
        raise RuntimeError("boom")


@pytest.mark.asyncio
async def test_capture_advertised_resources_prompts() -> None:
    @dataclass
    class R:
        uri: str

    @dataclass
    class P:
        name: str

    class FullSession:
        async def list_tools(self) -> Any:
            return []

        async def list_resources(self) -> Any:
            return [R("file:///a")]

        async def list_prompts(self) -> Any:
            return [P("summarize")]

    await capture_advertised_inventory(FullSession())
    state = get_coverage(FullSession())
    assert "summarize" not in state.advertised_prompts  # new session


@pytest.mark.asyncio
async def test_capture_advertised_resources_prompts_on_session() -> None:
    @dataclass
    class R:
        uri: str

    @dataclass
    class P:
        name: str

    class FullSession:
        async def list_tools(self) -> Any:
            return type("T", (), {"tools": []})()

        async def list_resources(self) -> Any:
            return type("T", (), {"resources": [R("file:///a")]})()

        async def list_prompts(self) -> Any:
            return type("T", (), {"prompts": [P("summarize")]})()

    s = FullSession()
    await capture_advertised_inventory(s)
    st = get_coverage(s)
    assert "file:///a" in st.advertised_resources
    assert "summarize" in st.advertised_prompts


@pytest.mark.asyncio
async def test_capture_dict_tool_names() -> None:
    class S:
        async def list_tools(self) -> Any:
            return {"tools": [{"name": "dict_tool"}]}

        async def list_resources(self) -> Any:
            return {"resources": [{"uri": "u://r"}]}

        async def list_prompts(self) -> Any:
            return {"prompts": [{"name": "dict_prompt"}]}

    s = S()
    await capture_advertised_inventory(s)
    st = get_coverage(s)
    assert "dict_tool" in st.advertised_tools
    assert "u://r" in st.advertised_resources
    assert "dict_prompt" in st.advertised_prompts


def test_coverage_session_dict_roundtrip() -> None:
    class S:
        pass

    s = S()
    a = get_coverage(s)
    a.tested_tools.add("x")
    b = get_coverage(s)
    assert b is a
    assert "x" in b.tested_tools

    class WeakSession:
        __slots__ = ("__weakref__",)

    session = WeakSession()
    state = get_coverage(session)
    state.tested_tools.add("t")
    state2 = get_coverage(session)
    assert state2 is state
    assert "t" in state2.tested_tools


def test_coverage_dict_assign_falls_back_to_weakref() -> None:
    class BadDict(dict):
        def __setitem__(self, key: str, value: object) -> None:
            raise TypeError("read-only")

    class Session:
        def __init__(self) -> None:
            self._store = BadDict()

        @property
        def __dict__(self) -> BadDict:
            return self._store

    s = Session()
    a = get_coverage(s)
    a.tested_tools.add("fallback")
    b = get_coverage(s)
    assert "fallback" in b.tested_tools


@pytest.mark.asyncio
async def test_capture_advertised_handles_list_errors() -> None:
    await capture_advertised_inventory(ExplodingSession())
    record_resource_read(object(), "file:///x")
    record_prompt(object(), "p")


def test_baseline_errors(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_baseline(tmp_path / "nope.json")
    bad = tmp_path / "bad.json"
    bad.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError):
        load_baseline(bad)
    save_baseline(tmp_path / "ok.json", {"m": 1.0}, metadata={"v": 1})
    with pytest.raises(MCPAssertionError, match="no metric key"):
        compare_metric("missing", 1.0, {"metrics": {}})
    with pytest.raises(MCPAssertionError, match="baseline 0"):
        compare_metric("m", 1.0, {"metrics": {"m": 0}})
    compare_metric("m", 0.0, {"metrics": {"m": 0}})


@pytest.mark.asyncio
async def test_latency_baseline_warmup(tmp_path: Path) -> None:
    from mcp_test_harness.baselines import assert_latency_within_baseline

    p = tmp_path / "b.json"
    save_baseline(p, {"k": 99999.0})

    class S:
        async def call_tool(self, *_a: Any, **_k: Any) -> None:
            return None

    await assert_latency_within_baseline(S(), "t", {}, p, "k", runs=1, warmup=1)


@pytest.mark.asyncio
async def test_injection_ignores_transport_errors() -> None:
    class ErrSession:
        async def call_tool(self, _n: str, _a: dict) -> ToolResult:
            raise OSError("transport down")

    await assert_injection_blocked(ErrSession(), "t", payloads=("x",))


@pytest.mark.asyncio
async def test_path_traversal_and_pack() -> None:
    class FileSession:
        async def call_tool(self, _n: str, args: dict) -> ToolResult:
            if "passwd" in str(args.get("path", "")):
                return ToolResult(content=[Content(text="root:x:0:0:root:/root:/bin/bash")])
            return ToolResult(content=[Content(text="denied", isError=True)])

    with pytest.raises(MCPAssertionError, match="path traversal"):
        await assert_path_traversal_blocked(
            FileSession(), "read", payloads=("/etc/passwd",)
        )

    class OkSession:
        async def call_tool(self, _n: str, _a: dict) -> ToolResult:
            return ToolResult(content=[Content(text="ok", isError=True)])

    await run_security_payload_pack(OkSession(), "t", path_argument="path")


@pytest.mark.asyncio
async def test_path_traversal_skips_transport_error() -> None:
    class ErrPath:
        async def call_tool(self, _n: str, _a: dict) -> ToolResult:
            raise OSError("down")

    await assert_path_traversal_blocked(ErrPath(), "r", payloads=("../x",))


@pytest.mark.asyncio
async def test_tool_response_text_dict_items() -> None:
    class DictSession:
        async def call_tool(self, _n: str, _a: dict) -> Any:
            return {"content": [{"text": "leak-me", "isError": False}]}

    with pytest.raises(MCPAssertionError):
        await assert_injection_blocked(DictSession(), "t", payloads=("leak-me",))


@pytest.mark.asyncio
async def test_resiliency_failure_paths() -> None:
    class PoisonSession:
        def __init__(self) -> None:
            self.n = 0

        async def call_tool(self, _n: str, args: dict) -> ToolResult:
            self.n += 1
            if args.get("__mcp_harness_probe_invalid__") and self.n == 1:
                raise ConnectionError("drop")
            if args.get("__mcp_harness_probe_invalid__"):
                return ToolResult(content=[Content(text="e", isError=True)])
            return ToolResult(content=[Content(text="still bad", isError=True)])

        async def list_tools(self) -> list:
            return []

    with pytest.raises(MCPAssertionError, match="still returns error"):
        await assert_reconnects(PoisonSession(), "t", {}, probe_errors=2)

    class Poison2:
        async def call_tool(self, _n: str, args: dict) -> ToolResult:
            if args.get("__mcp_harness_error_burst__"):
                raise RuntimeError("x")
            return ToolResult(content=[Content(text="e", isError=True)])

    with pytest.raises(MCPAssertionError, match="unavailable after error burst"):
        await assert_survives_crash(Poison2(), "t", {})


def test_json_and_html_unified_portal() -> None:
    cov = {
        "gaps": {"untested_tools": ["a"], "tools_missing_auth_tests": ["b"]},
        "summary": {"tools_tested": 1},
    }
    results = SessionResults(
        test_results=[
            CaseResult("s", "m", CaseStatus.PASSED, 1.0, tags=["security"]),
            CaseResult("r", "m", CaseStatus.PASSED, 1.0, tags=["resiliency"]),
        ],
        total_duration_ms=2.0,
        server_capabilities={},
        protocol_version="1",
        harness_version="1.1.0",
        passed=2,
        coverage=cov,
    )
    results.unified_summary = build_unified_summary(results, cov)
    raw = JSONReporter().generate(results)
    data = json.loads(raw)
    assert "unified_summary" in data
    assert "coverage" in data
    html = HTMLReporter().generate(results)
    assert "Unified test portal" in html
    assert "untested tool" in html
