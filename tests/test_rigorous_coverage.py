"""Targeted tests for full line coverage on framework modules (see pyproject coverage)."""

from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_test_harness import assertions as ass
from mcp_test_harness.cli import _test_tree_snapshot
from mcp_test_harness.config import (
    HarnessConfig,
    _find_yaml_line,
    validate_config_file,
)
from mcp_test_harness.discovery import HarnessCase, discover_tests
from mcp_test_harness.fixtures import FixtureManager, register_builtin_fixtures
from mcp_test_harness.models import CaseStatus, JsonRpcError, ParsedMessage, SchemaViolation
from mcp_test_harness.parser import pretty_print
from mcp_test_harness.plugins import PluginRegistry
from mcp_test_harness.schema import SchemaValidator, validate_mcp_server_after_connect
from mcp_test_harness.lifecycle import StartupError
from mcp_test_harness.scheduler import HarnessScheduler, _assert_mcp_compliance
from mcp_test_harness.transport import (
    SSETransportAdapter,
    StreamableHTTPTransportAdapter,
    StdioTransportAdapter,
)


# ---------------------------------------------------------------------------
# Assertions
# ---------------------------------------------------------------------------


class TestSerializeAndHelpers:
    def test_serialize_dunder_dict_object(self) -> None:
        class O:
            def __init__(self) -> None:
                self.x = 1
                self._hidden = 2

        assert ass._serialize(O()) == {"x": 1}

    def test_drop_and_mask(self) -> None:
        d = {"a": 1, "b": {"rid": 2}}
        assert ass._drop_field_paths(d, None) == d
        out2 = ass._drop_field_paths(d, ["rid"])
        assert "rid" not in str(out2)
        s = ass._apply_mask_strings("abc req_123", [re.compile(r"req_\w+")])
        assert "<masked>" in s


@pytest.mark.asyncio
class TestAssertionAsync:
    async def test_validate_args_happy(self) -> None:
        pytest.importorskip("jsonschema")
        t = SimpleNamespace(
            name="n",
            inputSchema={"type": "object", "properties": {"x": {"type": "string"}}},
        )
        session = MagicMock()
        session.list_tools = AsyncMock(return_value=SimpleNamespace(tools=[t]))
        await ass._validate_arguments_against_schema(session, "n", {"x": "a"})

    async def test_validate_args_mismatch(self) -> None:
        pytest.importorskip("jsonschema")
        t = SimpleNamespace(
            name="n",
            inputSchema={"type": "object", "properties": {"x": {"type": "string"}}},
        )
        session = MagicMock()
        session.list_tools = AsyncMock(return_value=SimpleNamespace(tools=[t]))
        with pytest.raises(ass.MCPAssertionError, match="inputSchema"):
            await ass._validate_arguments_against_schema(session, "n", {"x": 1})

    async def test_assert_tool_call_validate_schema(self) -> None:
        pytest.importorskip("jsonschema")
        t = SimpleNamespace(
            name="n",
            inputSchema={"type": "object", "properties": {"x": {"type": "string"}}},
        )
        session = MagicMock()
        session.list_tools = AsyncMock(return_value=SimpleNamespace(tools=[t]))
        session.call_tool = AsyncMock(return_value=SimpleNamespace(content=[]))
        await ass.assert_tool_call(
            session, "n", {"x": "ok"}, validate_against_input_schema=True
        )
        with pytest.raises(ass.MCPAssertionError):
            await ass.assert_tool_call(
                session, "n", {"x": 3}, validate_against_input_schema=True
            )

    async def test_assert_capabilities_serializes_to_non_dict(self) -> None:
        session = MagicMock()
        session.server_capabilities = 42
        await ass.assert_capabilities(session, {})

    async def test_assert_capabilities_uses_mcp_harness_init_result(self) -> None:
        from types import SimpleNamespace

        s = SimpleNamespace()
        s._mcp_harness_init_result = SimpleNamespace(
            capabilities={"sampling": {}, "tools": {"listChanged": True}}
        )
        await ass.assert_capabilities(s, {"tools": {"listChanged": True}})

    async def test_assert_capabilities_init_result_dict(self) -> None:
        from types import SimpleNamespace

        s = SimpleNamespace()
        s._mcp_harness_init_result = {
            "capabilities": {"sampling": {}, "x": 1},
        }
        await ass.assert_capabilities(s, {"x": 1})

    async def test_assert_tool_schema_mismatch(self) -> None:
        t = SimpleNamespace(
            name="e",
            inputSchema={"type": "object", "title": "x"},
        )
        session = MagicMock()
        session.list_tools = AsyncMock(return_value=SimpleNamespace(tools=[t]))
        with pytest.raises(ass.MCPAssertionError, match="inputSchema"):
            await ass.assert_tool_schema(
                session, "e", {"type": "object", "title": "y"},
            )

    async def test_assert_tool_schema_not_dict(self) -> None:
        t = SimpleNamespace(name="e", inputSchema=123)
        session = MagicMock()
        session.list_tools = AsyncMock(return_value=SimpleNamespace(tools=[t]))
        with pytest.raises(ass.MCPAssertionError, match="no dict inputSchema"):
            await ass.assert_tool_schema(session, "e", {"type": "object"})

    async def test_assert_protocol_version_bad(self) -> None:
        session = MagicMock()
        session._mcp_harness_init_result = SimpleNamespace(
            protocolVersion="old",
        )
        with pytest.raises(ass.MCPAssertionError, match="protocolVersion"):
            await ass.assert_protocol_version(session, "2024-11-05")

    async def test_assert_protocol_version_dict_ir(self) -> None:
        session = MagicMock()
        object.__setattr__(
            session,
            "_mcp_harness_init_result",
            {"protocolVersion": 99},
        )
        with pytest.raises(ass.MCPAssertionError):
            await ass.assert_protocol_version(session, "2024-11-05")

    async def test_idempotent_mismatch(self) -> None:
        n = 0
        session = MagicMock()

        async def call_tool(*_a, **_k):
            nonlocal n
            n += 1
            return SimpleNamespace(content=[{"k": n}])

        session.call_tool = call_tool
        with pytest.raises(ass.MCPAssertionError, match="differing"):
            await ass.assert_tool_idempotent(session, "t", {}, runs=2)

    async def test_latency_exceeds(self) -> None:
        import asyncio

        async def slow(*_a, **_k):
            await asyncio.sleep(0.2)

        session = MagicMock()
        session.call_tool = slow
        with pytest.raises(ass.MCPAssertionError, match="exceeds budget"):
            await ass.assert_latency(session, "t", {}, max_ms=1)

    async def test_snapshot_ignore_mask(self, tmp_path: Path) -> None:
        f = tmp_path / "t.py"
        f.write_text("#", encoding="utf-8")
        await ass.assert_snapshot(
            {"a": 1, "req_abc": "x"},
            "m",
            f,
            ignore_fields=["b"],
            mask_patterns=[r"req_[a-z]+"],
        )


# ---------------------------------------------------------------------------
# CLI snapshot
# ---------------------------------------------------------------------------


def test_test_tree_snapshot_file_and_dir(tmp_path: Path) -> None:
    a = tmp_path / "a.py"
    a.write_text("x", encoding="utf-8")
    t1 = _test_tree_snapshot([a, tmp_path])
    a.write_text("y", encoding="utf-8")
    t2 = _test_tree_snapshot([a, tmp_path])
    assert t1 != t2


def test_test_tree_snapshot_stat_oserror(tmp_path: Path) -> None:
    sub = tmp_path / "s.py"
    sub.write_text("1", encoding="utf-8")
    real = Path.stat

    def stat_sel(self: Path, *args: object, **kwargs: object) -> object:
        if self == sub:
            raise OSError("x")
        return real(self, *args, **kwargs)

    with patch.object(Path, "stat", stat_sel):
        out = _test_tree_snapshot([tmp_path])
    assert out == ()


# ---------------------------------------------------------------------------
# config
# ---------------------------------------------------------------------------


def test_find_yaml_line_not_found() -> None:
    assert _find_yaml_line("foo: 1", "nope") is None


def test_validate_config_toml_unknown_server_key(tmp_path: Path) -> None:
    f = tmp_path / "mcp-test.toml"
    f.write_text(
        '[server]\ncommand = "c"\nunknown_key = 1\n',
        encoding="utf-8",
    )
    err = validate_config_file(f)
    assert any("Unknown key" in e.message for e in err)


# ---------------------------------------------------------------------------
# discovery
# ---------------------------------------------------------------------------


def test_discover_test_class_non_callable_test(tmp_path: Path) -> None:
    p = tmp_path / "t.py"
    p.write_text(
        "class T:\n"
        "    test_ok = 1\n"
        "    test_none = None\n",
        encoding="utf-8",
    )
    assert discover_tests([tmp_path]) == []


# ---------------------------------------------------------------------------
# parser
# ---------------------------------------------------------------------------


def test_pretty_print_error_with_data() -> None:
    m = ParsedMessage(
        id=1,
        method=None,
        params=None,
        result=None,
        error=JsonRpcError(code=1, message="e", data={"x": 1}),
        raw=b"{}",
    )
    t = pretty_print(m, syntax_highlight=True)
    assert "Error" in t and "e" in t


# ---------------------------------------------------------------------------
# schema
# ---------------------------------------------------------------------------


class TestSchemaBranches:
    def test_text_content_bad(self) -> None:
        v = SchemaValidator(True)
        bad = [SimpleNamespace(type="text", text=123)]
        assert v.validate_content_items_shape(bad)

    def test_image_content_bad(self) -> None:
        v = SchemaValidator(True)
        bad = [SimpleNamespace(type="image", data=1, mimeType="x")]
        r = v.validate_content_items_shape(bad)
        assert any("data" in x.message for x in r)

    def test_list_resources_mime_not_str(self) -> None:
        v = SchemaValidator(True)
        r = v.validate_list_resources_shape(
            [SimpleNamespace(uri="u://a", name="n", mimeType=99)]
        )
        assert r

    @pytest.mark.asyncio
    async def test_validate_connect_list_tools_fails(self) -> None:
        session = MagicMock()
        session.list_tools = AsyncMock(side_effect=RuntimeError("nope"))
        v = await validate_mcp_server_after_connect(
            session,
            SimpleNamespace(
                protocolVersion="1",
                capabilities={},
                serverInfo=SimpleNamespace(name="n", version="1"),
            ),
            SchemaValidator(True),
        )
        assert any("list_tools" in x.message for x in v)

    @pytest.mark.asyncio
    async def test_list_prompts_raises_skipped(self) -> None:
        session = MagicMock()
        session.list_tools = AsyncMock(
            return_value=SimpleNamespace(
                tools=[
                    SimpleNamespace(
                        name="t",
                        description="d",
                        inputSchema={"type": "object", "properties": {}},
                    )
                ],
            )
        )
        session.list_resources = AsyncMock(return_value=SimpleNamespace(resources=[]))
        session.list_prompts = AsyncMock(side_effect=TypeError("no"))
        session.call_tool = AsyncMock(
            return_value=SimpleNamespace(content=[])
        )
        v = await validate_mcp_server_after_connect(
            session,
            SimpleNamespace(
                protocolVersion="1",
                capabilities={},
                serverInfo=SimpleNamespace(name="n", version="1"),
            ),
            SchemaValidator(True),
        )
        assert isinstance(v, list)


# ---------------------------------------------------------------------------
# transport
# ---------------------------------------------------------------------------


class TestTransportsConnect:
    @pytest.mark.asyncio
    async def test_sse(self) -> None:
        a = SSETransportAdapter(url="http://x/sse")
        with patch("mcp.client.sse.sse_client") as sc:
            sc.return_value.__aenter__ = AsyncMock(
                return_value=(MagicMock(), MagicMock())
            )
            sc.return_value.__aexit__ = AsyncMock()
            await a.connect()
        await a.close()

    @pytest.mark.asyncio
    async def test_http(self) -> None:
        a = StreamableHTTPTransportAdapter(url="http://x/m")
        with patch("mcp.client.streamable_http.streamablehttp_client") as sc:
            sc.return_value.__aenter__ = AsyncMock(
                return_value=(MagicMock(), MagicMock(), "sid")
            )
            sc.return_value.__aexit__ = AsyncMock()
            await a.connect()
        await a.close()


@pytest.mark.asyncio
async def test_stdio_empty_command() -> None:
    a = StdioTransportAdapter("   ")
    with pytest.raises(ValueError, match="empty"):
        await a.connect()


# ---------------------------------------------------------------------------
# scheduler
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mcp_compliance_raises() -> None:
    srv = SimpleNamespace(session=MagicMock(), init_result=object())
    cfg = HarnessConfig(server_command="c", schema_validation=True)

    async def bad(_s, _i, _v, **_kwargs):
        return [SchemaViolation("a", "b", None, "bad")]

    with (
        patch(
            "mcp_test_harness.scheduler.validate_mcp_server_after_connect",
            bad,
        ),
        pytest.raises(StartupError, match="MCP protocol validation failed"),
    ):
        await _assert_mcp_compliance(cfg, srv)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_parallel_worker_startup_fails() -> None:
    async def _fn() -> None:
        pass

    tc = HarnessCase(
        name="t",
        module_path=Path("m.py"),
        func=_fn,
        markers={},
        is_async=True,
    )
    cfg = HarnessConfig(server_command="c", schema_validation=False)
    with patch("mcp_test_harness.scheduler.ServerLifecycleManager") as m:
        m.return_value.start = AsyncMock(side_effect=RuntimeError("fail"))
        m.return_value.shutdown = AsyncMock()
        r = await HarnessScheduler().run_parallel([tc], cfg, workers=1)
    assert r.test_results[0].status == CaseStatus.ERROR
    assert "failed" in (r.test_results[0].error or "").lower()


# ---------------------------------------------------------------------------
# plugins
# ---------------------------------------------------------------------------


def test_entry_points_query_fail() -> None:
    with (
        patch(
            "mcp_test_harness.plugins.importlib.metadata.entry_points",
            side_effect=OSError,
        ),
    ):
        PluginRegistry()._load_from_entry_points()  # noqa: SLF001


# ---------------------------------------------------------------------------
# fixtures: per-test cache hit (line 220–222)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fixture_dep_reuses_cached_a() -> None:
    async def a() -> int:
        return 7

    async def b(a: int) -> int:
        return a + 1

    mgr = FixtureManager()
    mgr.set_injected("managed_server", object())
    register_builtin_fixtures(mgr)
    mgr.register("a", a)
    mgr.register("b", b)

    async def t(a: int, b: int) -> None:  # noqa: ARG001
        assert a == 7 and b == 8

    await mgr.resolve(t)
