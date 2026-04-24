"""Extra line coverage to satisfy fail_under=100 (framework source only, per pyproject)."""

from __future__ import annotations

import asyncio
import os
import re
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import mcp_test_harness.assertions as ass
from mcp_test_harness.assertions import (
    assert_protocol_version,
    assert_tool_call_validates_input,
    assert_tool_schema,
)
from mcp_test_harness.cli import _async_main
from mcp_test_harness.config import HarnessConfig
from mcp_test_harness.discovery import HarnessCase, _load_module_from_path, discover_tests
from mcp_test_harness.executor import CaseExecutor
from mcp_test_harness.fixtures import FixtureManager, FixtureScope, register_builtin_fixtures
from mcp_test_harness.lifecycle import ManagedServer, ServerCrashedError, ServerLifecycleManager
from mcp_test_harness.models import CaseResult, CaseStatus, ParsedMessage
from mcp_test_harness.parser import pretty_print
from mcp_test_harness.plugins import PluginRegistry
from mcp_test_harness.schema import SchemaValidator, _type_name
from mcp_test_harness.scheduler import HarnessScheduler, _assert_mcp_compliance
from mcp_test_harness.transport import StdioTransportAdapter


def _case(name: str, mod: str) -> HarnessCase:
    async def _f() -> None:
        return

    return HarnessCase(
        name=name,
        module_path=Path(mod),
        func=_f,
        markers={},
        is_async=True,
    )


def _make_cfg(**kw: object) -> HarnessConfig:
    d: dict = dict(
        server_command="echo",
        transport="stdio",
        timeout=2.0,
        schema_validation=False,
    )
    d.update(kw)
    return HarnessConfig(**d)


def _server_sched() -> ManagedServer:
    return ManagedServer(
        process=None,
        session=MagicMock(),
        transport=MagicMock(),
        capabilities={"protocolVersion": "2024-11-05", "x": 1},
    )


# -- assertions --


def test_serialize_no_dict_uses_str() -> None:
    class S:
        __slots__ = ()

    assert isinstance(ass._serialize(S()), str)


def test_drop_keys_on_list() -> None:
    out = ass._drop_keys([{"a": 1, "b": 2}], {"b"})
    assert out == [{"a": 1}]


def test_mask_strings_list() -> None:
    p = re.compile("x")
    assert ass._apply_mask_strings(["ax", "y"], [p]) == ["a<masked>", "y"]


@pytest.mark.asyncio
async def test_validate_args_input_schema_not_dict() -> None:
    pytest.importorskip("jsonschema")
    t = {"name": "n", "inputSchema": 99}
    s = MagicMock()
    s.list_tools = AsyncMock(return_value=SimpleNamespace(tools=[t]))
    await ass._validate_arguments_against_schema(s, "n", {"x": 1})


@pytest.mark.asyncio
async def test_validate_args_dict_tool_and_no_match() -> None:
    pytest.importorskip("jsonschema")
    t = {
        "name": "n",
        "inputSchema": {"type": "object", "properties": {"x": {"type": "string"}}},
    }
    s = MagicMock()
    s.list_tools = AsyncMock(return_value=SimpleNamespace(tools=[t]))
    await ass._validate_arguments_against_schema(s, "n", {"x": "ok"})

    s2 = MagicMock()
    s2.list_tools = AsyncMock(return_value=SimpleNamespace(tools=[t]))
    await ass._validate_arguments_against_schema(s2, "other", {"x": "ok"})


@pytest.mark.asyncio
async def test_assert_tool_schema_dict_tool_not_found() -> None:
    s = MagicMock()
    s.list_tools = AsyncMock(
        return_value=SimpleNamespace(
            tools=[{"name": "a", "inputSchema": {"type": "object"}}],
        ),
    )
    with pytest.raises(ass.MCPAssertionError, match="not found"):
        await assert_tool_schema(s, "missing", {"type": "object"})


@pytest.mark.asyncio
async def test_assert_protocol_version_no_stashed_result() -> None:
    s = MagicMock(spec=[])
    with pytest.raises(ass.MCPAssertionError, match="No initialize result"):
        await assert_protocol_version(s, "2024-11-05")


@pytest.mark.asyncio
async def test_assert_tool_call_validates_input_rejects() -> None:
    s = MagicMock()
    s.call_tool = AsyncMock(
        return_value=SimpleNamespace(
            isError=True,
            content=[{"type": "text", "text": "bad", "isError": True}],
        )
    )
    await assert_tool_call_validates_input(s, "t", {"x": 1})


@pytest.mark.asyncio
async def test_assert_tool_schema_dict_isc_match_and_mismatch() -> None:
    s = MagicMock()
    s.list_tools = AsyncMock(
        return_value=SimpleNamespace(
            tools=[{"name": "e", "inputSchema": {"type": "object", "title": "a"}}],
        )
    )
    with pytest.raises(ass.MCPAssertionError, match="does not match"):
        await assert_tool_schema(s, "e", {"type": "object", "title": "b"})
    s2 = MagicMock()
    s2.list_tools = AsyncMock(
        return_value=SimpleNamespace(
            tools=[{"name": "e", "inputSchema": {"type": "object"}}],
        )
    )
    await assert_tool_schema(s2, "e", {"type": "object"})


@pytest.mark.asyncio
async def test_assert_tool_schema_no_tool_found() -> None:
    s = MagicMock()
    s.list_tools = AsyncMock(
        return_value=SimpleNamespace(
            tools=[{"name": "a", "inputSchema": {"type": "object"}}],
        )
    )
    with pytest.raises(ass.MCPAssertionError, match="not found via list"):
        await assert_tool_schema(s, "z", {"type": "object"})


# -- cli & watch --


@pytest.mark.asyncio
async def test_async_main_watch_max_outer() -> None:
    cfg = HarnessConfig(
        server_command="echo a",
        test_dirs=["."],
        report_format="console",
        report_output=None,
        schema_validation=False,
    )
    with (
        patch.dict(os.environ, {"MCP_TEST_HARNESS_WATCH_MAX_OUTER": "1"}),
        patch("mcp_test_harness.cli._run_harness", new_callable=AsyncMock) as r,
        patch("mcp_test_harness.cli.load_config", return_value=cfg),
    ):
        r.return_value = 0
        code = await _async_main([".", "--watch", "--server-command", "x"])
    assert code == 0
    r.assert_awaited()


@pytest.mark.asyncio
async def test_async_main_html_report_write(tmp_path: Path) -> None:
    from mcp_test_harness.discovery import HarnessModule
    from mcp_test_harness.models import SessionResults, CaseResult, CaseStatus

    rep = tmp_path / "o.html"
    d = str(tmp_path)
    cfg = HarnessConfig(
        server_command="echo a",
        test_dirs=[d],
        report_format="html",
        report_output=str(rep),
        schema_validation=False,
    )
    tc = _case("t", "m.py")
    hmod = HarnessModule(path=Path("m.py"), test_cases=[tc])
    ses = SessionResults(
        test_results=[CaseResult("t", "m.py", CaseStatus.PASSED, 1.0)],
        total_duration_ms=1.0,
        server_capabilities={},
        protocol_version="",
        harness_version="0.1.0",
        passed=1,
    )
    with (
        patch("mcp_test_harness.cli.discover_tests", return_value=[hmod]),
        patch("mcp_test_harness.scheduler.HarnessScheduler") as hs,
        patch("mcp_test_harness.plugins.PluginRegistry") as prg,
        patch("mcp_test_harness.cli.load_config", return_value=cfg),
    ):
        prg.return_value.discover_and_load = MagicMock()
        hs.return_value.run_sequential = AsyncMock(return_value=ses)
        code = await _async_main(
            [d, "--server-command", "echo a", "--report-format", "html", "--report-output", str(rep)],
        )
    assert code == 0
    assert rep.is_file()
    txt = rep.read_text(encoding="utf-8")
    assert "html" in txt.lower() or len(txt) > 10


@pytest.mark.asyncio
async def test_async_main_junit_report_write(tmp_path: Path) -> None:
    from mcp_test_harness.discovery import HarnessModule
    from mcp_test_harness.models import SessionResults, CaseResult, CaseStatus

    rep = tmp_path / "o.xml"
    d = str(tmp_path)
    cfg = HarnessConfig(
        server_command="echo a",
        test_dirs=[d],
        report_format="junit",
        report_output=str(rep),
        schema_validation=False,
    )
    tc = _case("t", "m.py")
    hmod = HarnessModule(path=Path("m.py"), test_cases=[tc])
    ses = SessionResults(
        test_results=[CaseResult("t", "m.py", CaseStatus.PASSED, 1.0)],
        total_duration_ms=1.0,
        server_capabilities={},
        protocol_version="",
        harness_version="0.1.0",
        passed=1,
    )
    with (
        patch("mcp_test_harness.cli.discover_tests", return_value=[hmod]),
        patch("mcp_test_harness.scheduler.HarnessScheduler") as hs,
        patch("mcp_test_harness.plugins.PluginRegistry") as prg,
        patch("mcp_test_harness.cli.load_config", return_value=cfg),
    ):
        prg.return_value.discover_and_load = MagicMock()
        hs.return_value.run_sequential = AsyncMock(return_value=ses)
        code = await _async_main(
            [d, "--server-command", "echo a", "--report-format", "junit", "--report-output", str(rep)],
        )
    assert code == 0
    assert rep.is_file() and len(rep.read_text(encoding="utf-8")) > 0


def test_cli_version_via_module_main() -> None:
    import subprocess
    import sys

    p = subprocess.run(
        [sys.executable, "-m", "mcp_test_harness.cli", "--version"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert p.returncode == 0
    assert "mcp-test" in (p.stdout + p.stderr)


# -- discovery --


def test_load_module_spec_is_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    f = tmp_path / "a.py"
    f.write_text("x=1", encoding="utf-8")
    with patch(
        "mcp_test_harness.discovery.importlib.util.spec_from_file_location",
        return_value=None,
    ):
        assert _load_module_from_path(f) is None


def test_discover_class_test_none_and_non_func_skipped(
    tmp_path: Path,
) -> None:
    p = tmp_path / "test_cp.py"
    p.write_text(
        "class TestTst:\n"
        "    test_n = None\n"
        "    test_bad = 1\n"
        "    def test_f(self) -> None:\n"
        "        pass\n",
        encoding="utf-8",
    )
    mods = discover_tests([tmp_path])
    names = [tc.name for m in mods for tc in m.test_cases]
    assert any("TestTst.test_f" in n for n in names)


# -- executor: fixture teardown error logs (225) --


@pytest.mark.asyncio
async def test_executor_teardown_error_warns() -> None:
    async def badg():
        yield 1
        raise RuntimeError("teardown oops")

    async def t(x: int) -> None:  # noqa: ARG001
        return

    fm = FixtureManager()
    register_builtin_fixtures(fm)
    fm.set_injected("managed_server", object())
    fm.register("x", badg)

    ex = CaseExecutor()
    tc = HarnessCase(
        name="n",
        module_path=Path("m.py"),
        func=t,
        markers={},
        is_async=True,
    )
    with patch("mcp_test_harness.executor.logger") as log:
        r = await ex.execute(
            tc,
            ManagedServer(
                process=None,
                session=MagicMock(),
                transport=MagicMock(),
                capabilities={},
            ),
            fm,
        )
    assert r.status == CaseStatus.PASSED
    assert any("teardown" in str(c.args) for c in log.warning.call_args_list)


# -- lifecycle --


@pytest.mark.asyncio
async def test_shutdown_timeout_kill_process_gone() -> None:
    proc = MagicMock()
    proc.pid = 3
    proc.terminate = MagicMock()

    proc.wait = AsyncMock(side_effect=ProcessLookupError)
    t = MagicMock()
    t.close = AsyncMock()
    srv = ManagedServer(
        process=proc,
        session=None,
        transport=t,
        capabilities={},
    )
    mgr = ServerLifecycleManager()
    with patch("mcp_test_harness.lifecycle.asyncio.wait_for", new_callable=AsyncMock) as wf:
        wf.side_effect = asyncio.TimeoutError
        await mgr.shutdown(srv)
    proc.kill.assert_called_once()


def test_extract_capabilities_exotic() -> None:
    ir = SimpleNamespace(
        protocolVersion="1",
        capabilities=object(),  # no model_dump, no __dict__
    )
    assert ServerLifecycleManager._extract_capabilities(ir) == {}


# -- parser --


def test_pretty_print_params_and_bools() -> None:
    m = ParsedMessage(
        id=1,
        method="m",
        params={"a": [True, False, None]},
        result=None,
        error=None,
        raw=b"{}",
    )
    t = pretty_print(m, syntax_highlight=True)
    assert "true" in t and "m" in t


# -- plugins: bad spec in _import_file (230) --


def test_plugin_file_spec_no_loader(tmp_path: Path) -> None:
    p = tmp_path / "p.py"
    p.write_text("x=1", encoding="utf-8")
    with patch("importlib.util.spec_from_file_location", return_value=SimpleNamespace(loader=None)):
        out = PluginRegistry()._import_file(str(p))  # noqa: SLF001
    assert out is None


# -- schema --


def test_type_name_null() -> None:
    assert _type_name(None) == "null"


def test_schema_disabled_methods_return_empty() -> None:
    v = SchemaValidator(False)
    assert v.validate_initialize_result(object()) == []
    assert v.validate_list_tools_shape([]) == []
    assert v.validate_list_resources_shape([]) == []
    assert v.validate_list_prompts_shape([]) == []
    assert v.validate_content_items_shape([]) == []


def test_schema_initialize_result_server_info_object_name_bad() -> None:
    v = SchemaValidator(True)
    sinfo = SimpleNamespace(name=99)  # not str; non-dict branch (492-501)
    ir = SimpleNamespace(
        protocolVersion=1,
        capabilities={},
        serverInfo=sinfo,
    )
    u = v.validate_initialize_result(ir)
    assert any("serverInfo" in v_.json_path for v_ in u)


def test_schema_list_tools_description_non_str() -> None:
    v = SchemaValidator(True)
    t = SimpleNamespace(
        name="a",
        description=99,  # type: ignore[call-arg]
        inputSchema={},
    )
    u = v.validate_list_tools_shape([t])
    assert u


def test_schema_list_resources_name_non_str() -> None:
    v = SchemaValidator(True)
    r0 = SimpleNamespace(
        uri="u://a",
        name=1,  # not str
        mimeType="t",
    )
    u = v.validate_list_resources_shape([r0])
    assert u


def test_schema_list_prompts_arguments_not_list() -> None:
    v = SchemaValidator(True)
    p0 = SimpleNamespace(
        name="p",
        arguments={},
    )
    u = v.validate_list_prompts_shape([p0])
    assert u


def test_validate_response_branches() -> None:
    v = SchemaValidator(True)
    r = v.validate_response(
        {
            "jsonrpc": "2.0",
            "id": 1.5,
            "error": {
                "code": None,
                "message": 99,
            },
        }
    )
    assert len(r) >= 2


def test_template_compile_warning(caplog: pytest.LogCaptureFixture) -> None:
    with patch(
        "mcp_test_harness.schema._template_to_regex",
        side_effect=re.error("bad"),
    ):
        v = SchemaValidator(True)
        v.validate_resource_uris(
            [SimpleNamespace(uri="u://x", name="n", mimeType="t")],
            [SimpleNamespace(uriTemplate="h")],
        )
    assert "template" in caplog.text.lower() or "compile" in caplog.text.lower()


def test_validate_initialize_result_branches() -> None:
    v = SchemaValidator(True)
    assert v.validate_initialize_result(None)
    o = object()
    assert v.validate_initialize_result(o)  # type: ignore[arg-type]
    d = {"protocolVersion": 1, "capabilities": {}, "serverInfo": {"name": 1}}
    assert any("name" in x.message for x in v.validate_initialize_result(d))


def test_list_tools_list_resources_list_prompts_shapes() -> None:
    v = SchemaValidator(True)
    assert v.validate_list_tools_shape(
        [SimpleNamespace(name=1, description="", inputSchema=[])],
    )
    assert v.validate_list_resources_shape(
        [SimpleNamespace(uri=1, name="n", mimeType="t")],
    )
    assert v.validate_list_prompts_shape(
        [SimpleNamespace(name=1, arguments={})],
    )


def test_content_item_missing_type() -> None:
    v = SchemaValidator(True)
    u = v.validate_content_items_shape([{"text": "x"}])
    assert any("type" in x.message for x in u)


def test_content_image_mime_violation() -> None:
    v = SchemaValidator(True)
    bad = [
        SimpleNamespace(type="image", data=1, mimeType=1),
    ]
    u = v.validate_content_items_shape(bad)
    assert any("mimeType" in x.message for x in u)


def test_jsonschema_schema_error() -> None:
    pytest.importorskip("jsonschema")
    v = SchemaValidator(True)
    u = v.validate_tool_schemas(
        [{"name": "t", "inputSchema": {"type": "object", "required": 1}}],
    )
    assert u


# -- transport stdio: non-empty command path --


@pytest.mark.asyncio
async def test_stdio_connect_mocked() -> None:
    @asynccontextmanager
    async def _fake(*_a: object, **_k: object):
        yield (MagicMock(), MagicMock(), MagicMock())

    a = StdioTransportAdapter("echo hi")
    with patch("mcp_test_harness.transport.stdio_client_exposing_process", _fake):
        r, w = await a.connect()
    assert r is not None
    await a.close()


# -- scheduler --


@pytest.mark.asyncio
async def test_assert_mcp_compliance_no_violations() -> None:
    srv = SimpleNamespace(session=MagicMock(), init_result=object())
    c = _make_cfg(schema_validation=True)
    with patch(
        "mcp_test_harness.scheduler.validate_mcp_server_after_connect",
        new=AsyncMock(return_value=[]),
    ):
        await _assert_mcp_compliance(c, srv)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_sequential_per_module_teardown() -> None:
    c1, c2 = _case("a", "m1.py"), _case("b", "m2.py")
    per_module: list[FixtureScope] = []
    otd = FixtureManager.teardown

    async def track(self, scope: FixtureScope) -> list[Exception]:
        per_module.append(scope)
        return await otd(self, scope)

    with (
        patch.object(FixtureManager, "teardown", track),
        patch("mcp_test_harness.scheduler.ServerLifecycleManager") as lm,
        patch("mcp_test_harness.scheduler.CaseExecutor") as ce,
    ):
        ms = _server_sched()
        lm.return_value.start = AsyncMock(return_value=ms)
        lm.return_value.shutdown = AsyncMock()
        lm.return_value.start_monitor = MagicMock()
        ok = CaseResult(
            name="x",
            module="m",
            status=CaseStatus.PASSED,
            duration_ms=1.0,
        )
        ce.return_value.execute = AsyncMock(return_value=ok)
        await HarnessScheduler().run_sequential([c1, c2], _make_cfg())
    assert FixtureScope.PER_MODULE in per_module


@pytest.mark.asyncio
async def test_sequential_server_crash_marks_following() -> None:
    c1, c2 = _case("a", "x.py"), _case("b", "x.py")
    with (
        patch("mcp_test_harness.scheduler.ServerLifecycleManager") as lm,
        patch("mcp_test_harness.scheduler.CaseExecutor") as ce,
    ):
        ms = _server_sched()
        lm.return_value.start = AsyncMock(return_value=ms)
        lm.return_value.shutdown = AsyncMock()
        lm.return_value.start_monitor = MagicMock()
        n = 0

        async def _ex(*_a: object, **_k: object) -> CaseResult:
            nonlocal n
            n += 1
            if n == 1:
                raise ServerCrashedError("e")
            return CaseResult(
                name="x", module="m", status=CaseStatus.PASSED, duration_ms=1.0,
            )

        ce.return_value.execute = _ex
        r = await HarnessScheduler().run_sequential([c1, c2], _make_cfg())
    assert r.errored >= 1


@pytest.mark.asyncio
async def test_parallel_server_crash_marks_following() -> None:
    c1, c2 = _case("a", "x.py"), _case("b", "x.py")
    with (
        patch("mcp_test_harness.scheduler.ServerLifecycleManager") as lm,
        patch("mcp_test_harness.scheduler.CaseExecutor") as ce,
    ):
        ms = _server_sched()
        lm.return_value.start = AsyncMock(return_value=ms)
        lm.return_value.shutdown = AsyncMock()
        lm.return_value.start_monitor = MagicMock()
        n = 0

        async def _ex2(*_a: object, **_k: object) -> CaseResult:
            nonlocal n
            n += 1
            if n == 1:
                raise ServerCrashedError("e")
            return CaseResult(
                name="x", module="m", status=CaseStatus.PASSED, duration_ms=1.0,
            )

        ce.return_value.execute = _ex2
        r = await HarnessScheduler().run_parallel(
            [c1, c2],
            _make_cfg(),
            workers=1,
        )
    assert r.errored >= 1
