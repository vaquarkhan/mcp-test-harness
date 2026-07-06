"""Tests for MCP trace capture, chaos faults, and mcp-test generate."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_test_harness.chaos import (
    ChaosConfig,
    ChaosFaultError,
    ChaosSession,
    _drift_result,
    _truncate_result,
    parse_chaos_from_markers,
    wrap_session_for_test,
)
from mcp_test_harness.generate import (
    _drift_report,
    _tool_name,
    _tool_schema,
    example_arguments,
    render_test_module,
    run_generate,
)
from mcp_test_harness.html_reporter import HTMLReporter, _trace_timeline_html
from mcp_test_harness.models import CaseResult, CaseStatus, SessionResults
from mcp_test_harness.reporting import JSONReporter
from mcp_test_harness.trace import (
    TraceRecorder,
    _payload_bytes,
    _safe_json,
    _stdio_pollution_hint,
    attach_trace,
)


class _FakeTool:
    def __init__(self, name: str, schema: dict | None = None) -> None:
        self.name = name
        self.inputSchema = schema or {"type": "object", "properties": {"q": {"type": "string"}}, "required": ["q"]}


class _Content:
    def __init__(self, text: str) -> None:
        self.text = text


class _Result:
    def __init__(self, text: str) -> None:
        self.content = [_Content(text)]


@pytest.mark.asyncio
async def test_traced_session_records_call_tool() -> None:
    inner = AsyncMock()
    inner.call_tool.return_value = _Result("ok")
    rec = TraceRecorder()
    session = attach_trace(inner, rec)
    await session.call_tool("echo", {"q": "hi"})
    assert len(rec.events) == 2
    assert rec.events[0]["direction"] == "request"
    assert rec.events[1]["direction"] == "response"


@pytest.mark.asyncio
async def test_traced_session_records_json_errors_as_pollution() -> None:
    inner = AsyncMock()
    inner.list_tools.side_effect = ValueError("Invalid JSON decode at line 1")
    rec = TraceRecorder()
    session = attach_trace(inner, rec)
    with pytest.raises(ValueError):
        await session.list_tools()
    assert rec.stdio_pollution
    assert rec.events[-1]["direction"] == "error"


def test_parse_chaos_from_tags() -> None:
    cfg = parse_chaos_from_markers({"tags": ["chaos", "chaos:truncate"]})
    assert cfg is not None
    assert cfg.truncate is True


def test_parse_chaos_faults_kwarg() -> None:
    cfg = parse_chaos_from_markers({"tags": ["chaos"], "chaos_faults": ["delay_ms:50", "503"]})
    assert cfg is not None
    assert cfg.delay_ms == 50.0
    assert cfg.inject_error is True


@pytest.mark.asyncio
async def test_chaos_injects_503() -> None:
    inner = AsyncMock()
    cfg = ChaosConfig(faults=["503"], inject_error=True)
    session = ChaosSession(inner, cfg)
    with pytest.raises(ChaosFaultError):
        await session.call_tool("t", {})


@pytest.mark.asyncio
async def test_chaos_truncates_response() -> None:
    inner = AsyncMock()
    inner.call_tool.return_value = _Result("x" * 40)
    cfg = ChaosConfig(faults=["truncate"], truncate=True)
    session = ChaosSession(inner, cfg)
    result = await session.call_tool("t", {})
    assert len(result.content[0].text) < 40


@pytest.mark.asyncio
async def test_wrap_session_for_test_applies_chaos() -> None:
    inner = AsyncMock()
    inner.call_tool.return_value = _Result("ok")
    wrapped, rec = wrap_session_for_test(inner, markers={"tags": ["chaos"], "chaos_faults": ["delay_ms:1"]})
    await wrapped.call_tool("t", {})
    assert rec.events


def test_example_arguments_from_schema() -> None:
    args = example_arguments(
        {"type": "object", "properties": {"n": {"type": "integer"}}, "required": ["n"]},
    )
    assert args == {"n": 1}


def test_render_test_module() -> None:
    src = render_test_module([_FakeTool("echo")])
    assert "test_tool_echo_happy_path" in src
    assert "assert_tool_call" in src


def test_trace_timeline_html() -> None:
    tr = CaseResult(
        name="t",
        module="m",
        status=CaseStatus.FAILED,
        duration_ms=1.0,
        mcp_trace={
            "event_count": 1,
            "events": [{"t_ms": 1.0, "direction": "request", "method": "tools/call", "bytes": 10, "payload": {}}],
            "stdio_pollution": [],
        },
    )
    html = _trace_timeline_html(tr)
    assert "MCP trace" in html
    assert "tools/call" in html


def test_json_report_includes_mcp_trace() -> None:
    tr = CaseResult(
        name="t",
        module="m",
        status=CaseStatus.PASSED,
        duration_ms=1.0,
        mcp_trace={"events": [{"direction": "request"}], "event_count": 1, "stdio_pollution": []},
    )
    data = json.loads(
        JSONReporter().generate(
            SessionResults(
                test_results=[tr],
                total_duration_ms=1.0,
                server_capabilities={},
                protocol_version="",
                harness_version="1.2.0",
                passed=1,
            ),
        ),
    )
    assert "mcp_trace" in data["tests"][0]


def test_html_report_renders_trace_block() -> None:
    tr = CaseResult(
        name="t",
        module="m.py",
        file="m.py",
        status=CaseStatus.FAILED,
        duration_ms=5.0,
        error="fail",
        mcp_trace={
            "event_count": 1,
            "events": [{"t_ms": 2.0, "direction": "response", "method": "tools/list", "bytes": 3, "payload": {}}],
            "stdio_pollution": ["bad json"],
        },
    )
    html = HTMLReporter().generate(
        SessionResults(
            test_results=[tr],
            total_duration_ms=5.0,
            server_capabilities={},
            protocol_version="",
            harness_version="1.2.0",
            failed=1,
        ),
    )
    assert "trace-block" in html
    assert "stdio pollution" in html.lower()


@pytest.mark.asyncio
async def test_run_generate_writes_file(tmp_path: Path) -> None:
    from mcp_test_harness.generate import run_generate_async

    fake_tool = _FakeTool("ping")
    with patch("mcp_test_harness.generate._fetch_tools", AsyncMock(return_value=[fake_tool])):
        code = await run_generate_async(
            ["--dir", str(tmp_path), "--force", "--server-command", "echo x"],
        )
    assert code == 0
    out = tmp_path / "tests" / "test_mcp_generated.py"
    assert out.is_file()
    assert "test_tool_ping_happy_path" in out.read_text(encoding="utf-8")


def test_safe_json_branches() -> None:
    assert _safe_json(None) is None
    assert _safe_json("x" * 5000).endswith("…")
    assert _safe_json({"a": 1}) == {"a": "1"}
    assert _safe_json([1, 2]) == ["1", "2"]

    @dataclass
    class M:
        x: int = 1

    class Dump:
        def model_dump(self) -> dict[str, int]:
            return {"y": 2}

    assert _safe_json(Dump()) == {"y": "2"}
    assert _safe_json(M()) == {"x": "1"}
    assert isinstance(_safe_json(object()), str)

    class ReprOnly:
        __slots__ = ("a",)

        def __repr__(self) -> str:
            return "z" * 5000

    ro = ReprOnly()
    assert str(_safe_json(ro)).endswith("…")
    assert _payload_bytes({"a": 1}) > 0
    assert _stdio_pollution_hint(Exception("network timeout")) is None


@pytest.mark.asyncio
async def test_traced_session_delegates_non_traced_attrs() -> None:
    inner = MagicMock()
    inner.custom_attr = 42
    session = attach_trace(inner, TraceRecorder())
    assert session.custom_attr == 42


def test_parse_chaos_defaults_and_invalid_delay() -> None:
    cfg = parse_chaos_from_markers({"tags": ["chaos"]})
    assert cfg is not None
    assert cfg.delay_ms == 100.0
    cfg2 = parse_chaos_from_markers({"tags": ["chaos"], "chaos_faults": ["delay_ms:bad", "slow"]})
    assert cfg2 is not None
    assert cfg2.delay_ms == 100.0
    assert parse_chaos_from_markers({"tags": ["smoke"]}) is None
    cfg3 = parse_chaos_from_markers({"chaos_faults": ["schema_drift", "partial"]})
    assert cfg3 is not None
    assert cfg3.schema_drift and cfg3.truncate


def test_truncate_dict_content() -> None:
    class R:
        content = [{"text": "abcdefghijklmnop"}]

    result = R()
    _truncate_result(result)
    assert len(result.content[0]["text"]) < 16


def test_drift_dict_content() -> None:
    class R:
        content = [{"text": json.dumps({"user_id": "2"})}]

    result = R()
    _drift_result(result)
    assert "id" in json.loads(result.content[0]["text"])
    assert _truncate_result(object()) is not None
    short = _Result("short")
    assert _truncate_result(short) is short
    long = _Result("x" * 20)
    _truncate_result(long)
    assert len(long.content[0].text) < 20
    drift_in = _Result(json.dumps({"user_id": "1"}))
    _drift_result(drift_in)
    data = json.loads(drift_in.content[0].text)
    assert "id" in data
    assert _drift_result(_Result("not-json")) is not None


@pytest.mark.asyncio
async def test_chaos_schema_drift_and_delay() -> None:
    inner = AsyncMock()
    inner.call_tool.return_value = _Result(json.dumps({"user_id": "9"}))
    cfg = ChaosConfig(faults=["schema_drift"], schema_drift=True, delay_ms=0.0)
    session = ChaosSession(inner, cfg)
    result = await session.call_tool("t", {})
    assert "__chaos_unexpected_nullable" in json.loads(result.content[0].text)


@pytest.mark.asyncio
async def test_chaos_delegates_list_tools() -> None:
    inner = AsyncMock()
    inner.list_tools.return_value = "ok"
    session = ChaosSession(inner, ChaosConfig())
    assert session.list_tools is not None


def test_wrap_preserves_init_result() -> None:
    inner = MagicMock()
    inner._mcp_harness_init_result = {"v": 1}
    wrapped, _ = wrap_session_for_test(inner, markers={})
    assert getattr(wrapped, "_mcp_harness_init_result", None) == {"v": 1}


def test_tool_name_and_schema_helpers() -> None:
    assert _tool_name({"name": "a"}) == "a"
    assert _tool_name(object()) == "unknown"
    assert _tool_schema({"inputSchema": {"type": "object"}})["type"] == "object"
    assert example_arguments({"properties": {"b": {"type": "boolean"}}})["b"] is True
    assert example_arguments({"properties": {"n": {"type": "number"}}})["n"] == 1.0
    assert example_arguments({"properties": {"a": {"type": "array"}}})["a"] == []
    assert example_arguments({"properties": {"o": {"type": "object"}}})["o"] == {}
    assert example_arguments({"properties": {"e": {"type": "string", "enum": ["x"]}}})["e"] == "x"


def test_render_no_tools_fallback() -> None:
    src = render_test_module([], include_edge_cases=False)
    assert "test_no_tools_discovered" in src


def test_drift_report(tmp_path: Path) -> None:
    p = tmp_path / "t.py"
    p.write_text('await assert_tool_call(mcp_server, "a", {})', encoding="utf-8")
    r = _drift_report(p, ["a", "b"])
    assert r["drift_detected"]
    assert "b" in r["tools_missing_from_tests"]


@pytest.mark.asyncio
async def test_generate_refuse_overwrite(tmp_path: Path) -> None:
    from mcp_test_harness.generate import run_generate_async

    out = tmp_path / "tests"
    out.mkdir()
    f = out / "test_mcp_generated.py"
    f.write_text("# existing", encoding="utf-8")
    with patch("mcp_test_harness.generate._fetch_tools", AsyncMock(return_value=[])):
        code = await run_generate_async(["--dir", str(tmp_path), "--server-command", "x"])
    assert code == 2


@pytest.mark.asyncio
async def test_fetch_tools_startup_error() -> None:
    from mcp_test_harness.generate import _fetch_tools
    from mcp_test_harness.lifecycle import StartupError

    with patch("mcp_test_harness.lifecycle.ServerLifecycleManager") as lm:
        inst = lm.return_value
        inst.start = AsyncMock(side_effect=StartupError("nope"))
        with pytest.raises(SystemExit):
            await _fetch_tools(MagicMock())


def test_failure_detail_legacy() -> None:
    tr = CaseResult(name="t", module="m", status=CaseStatus.PASSED, duration_ms=1.0)
    assert HTMLReporter()._failure_detail(tr) == "—"


def test_trace_recorder_to_dict() -> None:
    rec = TraceRecorder()
    rec.record_request("m", {})
    d = rec.to_dict()
    assert d["event_count"] == 1


def test_generate_edge_helpers() -> None:
    assert _tool_schema(MagicMock(inputSchema="bad")) == {}
    assert example_arguments({"properties": "bad"}) == {}
    assert example_arguments({"properties": {"k": "bad"}, "required": ["k"]})["k"] == "example_k"
    src = render_test_module([{"name": ""}, {"no": "name"}], include_edge_cases=False)
    assert "test_no_tools_discovered" in src


@pytest.mark.asyncio
async def test_fetch_tools_shutdown_called() -> None:
    from mcp_test_harness.generate import _fetch_tools

    server = MagicMock()
    server.session.list_tools = AsyncMock(return_value=MagicMock(tools=[]))
    with patch("mcp_test_harness.lifecycle.ServerLifecycleManager") as lm:
        inst = lm.return_value
        inst.start = AsyncMock(return_value=server)
        inst.shutdown = AsyncMock()
        tools = await _fetch_tools(MagicMock())
        assert tools == []
        inst.shutdown.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_load_config_exit() -> None:
    from mcp_test_harness.generate import run_generate_async

    with patch("mcp_test_harness.config.load_config", side_effect=SystemExit(2)):
        assert await run_generate_async(["--server-command", "x"]) == 2


@pytest.mark.asyncio
async def test_generate_drift_report_on_refuse(tmp_path: Path) -> None:
    from mcp_test_harness.generate import run_generate_async

    out = tmp_path / "tests"
    out.mkdir()
    f = out / "test_mcp_generated.py"
    f.write_text("# existing", encoding="utf-8")
    drift = tmp_path / "drift.json"
    with patch("mcp_test_harness.generate._fetch_tools", AsyncMock(return_value=[_FakeTool("a")])):
        code = await run_generate_async(
            ["--dir", str(tmp_path), "--server-command", "x", "--drift-report", str(drift)],
        )
    assert code == 2
    assert drift.is_file()


@pytest.mark.asyncio
async def test_generate_writes_drift_after_success(tmp_path: Path) -> None:
    from mcp_test_harness.generate import run_generate_async

    drift = tmp_path / "drift.json"
    with patch("mcp_test_harness.generate._fetch_tools", AsyncMock(return_value=[_FakeTool("z")])):
        code = await run_generate_async(
            [
                "--dir", str(tmp_path), "--force", "--server-command", "x",
                "--drift-report", str(drift),
            ],
        )
    assert code == 0
    assert drift.is_file()


def test_drift_no_content() -> None:
    assert _drift_result(object()) is not None


def test_truncate_empty_items_iter() -> None:
    class Weird:
        content = iter(())

    weird = Weird()
    assert _truncate_result(weird) is weird


def test_drift_skips_non_string_text() -> None:
    class R:
        content = [object()]

    assert _drift_result(R()) is not None


def test_chaos_empty_content() -> None:
    class Empty:
        content = []

    assert _truncate_result(Empty()) is not None

    class NoText:
        content = [object()]

    _truncate_result(NoText())


def test_safe_json_model_dump_raises() -> None:
    class Bad:
        def model_dump(self) -> dict:
            raise ValueError("nope")

        def __init__(self) -> None:
            self.x = 1

    assert _safe_json(Bad()) == {"x": "1"}

    with patch("mcp_test_harness.trace.json.dumps", side_effect=TypeError("x")):
        assert _payload_bytes({}) == 0


def test_wrap_setattr_swallowed() -> None:
    inner = MagicMock()
    inner._mcp_harness_init_result = {"a": 1}
    with patch("mcp_test_harness.chaos.setattr", side_effect=TypeError("blocked")):
        wrap_session_for_test(inner, markers={})


def test_run_generate_sync_entry() -> None:
    with patch("asyncio.run", return_value=0):
        assert run_generate(["--server-command", "x"]) == 0