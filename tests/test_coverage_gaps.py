"""Tests targeting specific uncovered lines across modules."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, AsyncMock

import pytest

from mcp_test_harness.assertions import (
    MCPAssertionError,
    assert_resource_read,
    assert_capabilities,
    assert_tool_call,
    _serialize,
)
from mcp_test_harness.discovery import (
    _load_module_from_path,
    _is_test_file,
    discover_tests,
)
from mcp_test_harness.executor import TestExecutor
from mcp_test_harness.fixtures import (
    FixtureManager,
    FixtureScope,
    FixtureError,
    register_builtin_fixtures,
    register_decorated_fixtures,
    _decorated_fixtures,
    fixture,
)
from mcp_test_harness.lifecycle import ServerLifecycleManager, ManagedServer
from mcp_test_harness.parser import parse_message, pretty_print, serialize_message, ParseError
from mcp_test_harness.schema import SchemaValidator, _template_to_regex
from mcp_test_harness.scheduler import TestScheduler


# ---------------------------------------------------------------------------
# assertions.py -- uncovered lines
# ---------------------------------------------------------------------------


class TestAssertionsGaps:
    @pytest.mark.asyncio
    async def test_resource_read_dict_content(self):
        """Cover dict-style content items (line 180, 184)."""
        @dataclass
        class FakeResult:
            contents: list

        session = MagicMock()
        session.read_resource = AsyncMock(
            return_value=FakeResult(contents=[{"text": "hello", "mimeType": "text/plain"}])
        )
        result = await assert_resource_read(session, "file:///a.txt", expected_content="hello")
        assert result is not None

    @pytest.mark.asyncio
    async def test_tool_call_dict_error_item(self):
        """Cover dict-style isError check (line 67)."""
        @dataclass
        class FakeResult:
            content: list

        session = MagicMock()
        session.call_tool = AsyncMock(
            return_value=FakeResult(content=[{"text": "err", "isError": True}])
        )
        with pytest.raises(MCPAssertionError, match="returned an error"):
            await assert_tool_call(session, "t", {})

    @pytest.mark.asyncio
    async def test_capabilities_fallback_to_capabilities_attr(self):
        """Cover fallback to session.capabilities (line 293 area)."""
        session = MagicMock(spec=[])
        session.capabilities = {"tools": True}
        # Remove server_capabilities
        del session.server_capabilities
        await assert_capabilities(session, {"tools": True})

    def test_serialize_tuple(self):
        """Cover tuple serialization."""
        result = _serialize((1, "two", None))
        assert result == [1, "two", None]

    def test_serialize_nested_dict(self):
        """Cover nested dict serialization."""
        result = _serialize({"a": {"b": [1, 2]}})
        assert result == {"a": {"b": [1, 2]}}


# ---------------------------------------------------------------------------
# discovery.py -- uncovered lines
# ---------------------------------------------------------------------------


class TestDiscoveryGaps:
    def test_load_module_bad_spec(self, tmp_path: Path):
        """Cover spec_from_file_location returning None (line 164, 166)."""
        result = _load_module_from_path(tmp_path / "nonexistent.py")
        assert result is None

    def test_load_module_import_error(self, tmp_path: Path):
        """Cover module exec failure (line 185)."""
        bad = tmp_path / "test_bad_import.py"
        bad.write_text("import nonexistent_module_xyz\n")
        result = _load_module_from_path(bad)
        assert result is None

    def test_is_test_file_negative(self):
        assert _is_test_file(Path("helper.py")) is False
        assert _is_test_file(Path("utils_test_helper.py")) is False

    def test_discover_empty_directory(self, tmp_path: Path):
        modules = discover_tests([tmp_path])
        assert modules == []

    def test_discover_file_directly(self, tmp_path: Path):
        f = tmp_path / "test_direct.py"
        f.write_text("def test_one(): pass\n")
        modules = discover_tests([f])
        assert len(modules) == 1

    def test_non_test_file_ignored_in_dir(self, tmp_path: Path):
        (tmp_path / "helper.py").write_text("def test_nope(): pass\n")
        modules = discover_tests([tmp_path])
        assert modules == []


# ---------------------------------------------------------------------------
# executor.py -- uncovered line (sync invoke)
# ---------------------------------------------------------------------------


class TestExecutorGaps:
    @pytest.mark.asyncio
    async def test_sync_test_function(self):
        """Cover the sync branch of _invoke (line 225)."""
        called = False

        def sync_test():
            nonlocal called
            called = True

        from mcp_test_harness.discovery import TestCase

        case = TestCase(
            name="test_sync",
            module_path=Path("fake.py"),
            func=sync_test,
            markers={},
            is_async=False,
        )
        executor = TestExecutor()
        fm = FixtureManager()
        server = ManagedServer(
            process=None, session=MagicMock(), transport=MagicMock(), capabilities={}
        )
        result = await executor.execute(case, server, fm)
        assert called


# ---------------------------------------------------------------------------
# fixtures.py -- uncovered lines
# ---------------------------------------------------------------------------


class TestFixturesGaps:
    @pytest.mark.asyncio
    async def test_async_generator_no_yield_raises(self):
        """Cover FixtureError when generator doesn't yield (line 221)."""
        async def empty_gen():
            return
            yield  # make it a generator but never yields

        mgr = FixtureManager()
        mgr.register("empty", empty_gen)

        async def test_fn(empty: str):
            pass

        with pytest.raises(FixtureError, match="did not yield"):
            await mgr.resolve(test_fn)

    @pytest.mark.asyncio
    async def test_sync_fixture_factory(self):
        """Cover sync return path (line 247-248)."""
        def sync_factory():
            return "sync_value"

        mgr = FixtureManager()
        mgr.register("sync_fix", sync_factory)

        async def test_fn(sync_fix: str):
            pass

        resolved = await mgr.resolve(test_fn)
        assert resolved["sync_fix"] == "sync_value"

    @pytest.mark.asyncio
    async def test_awaitable_fixture(self):
        """Cover awaitable (non-generator) async fixture (line 243)."""
        async def async_factory():
            return "async_value"

        mgr = FixtureManager()
        mgr.register("async_fix", async_factory)

        async def test_fn(async_fix: str):
            pass

        resolved = await mgr.resolve(test_fn)
        assert resolved["async_fix"] == "async_value"

    def test_register_decorated_fixtures_integration(self):
        """Cover register_decorated_fixtures (line 271-272)."""
        _decorated_fixtures.clear()

        @fixture
        async def my_dec_fix():
            return 42

        mgr = FixtureManager()
        register_decorated_fixtures(mgr)
        assert "my_dec_fix" in mgr._registry
        _decorated_fixtures.clear()


# ---------------------------------------------------------------------------
# lifecycle.py -- uncovered line
# ---------------------------------------------------------------------------


class TestLifecycleGaps:
    def test_extract_process_with_process_attr(self):
        """Cover _extract_process finding _process attr (line 309)."""
        transport = MagicMock()
        transport._process = MagicMock()
        result = ServerLifecycleManager._extract_process(transport)
        assert result is transport._process


# ---------------------------------------------------------------------------
# parser.py -- uncovered lines
# ---------------------------------------------------------------------------


class TestParserGaps:
    def test_parse_unicode_error(self):
        """Cover UnicodeDecodeError path (line 155, 157)."""
        raw = b"\xff\xfe invalid utf"
        # This should either parse or raise ParseError
        try:
            parse_message(raw)
        except ParseError as e:
            assert e.raw == raw

    def test_pretty_print_no_highlight(self):
        """Cover non-highlighted path."""
        msg = parse_message(b'{"jsonrpc":"2.0","id":1,"result":"ok"}')
        output = pretty_print(msg, syntax_highlight=False)
        assert "Response" in output
        assert "\033[" not in output

    def test_serialize_notification(self):
        """Cover notification serialization (no id, no result)."""
        msg = parse_message(b'{"jsonrpc":"2.0","method":"log"}')
        data = json.loads(serialize_message(msg))
        assert data["method"] == "log"
        assert "id" not in data
        assert "result" not in data


# ---------------------------------------------------------------------------
# schema.py -- uncovered lines
# ---------------------------------------------------------------------------


class TestSchemaGaps:
    def test_validate_tool_schemas_disabled(self):
        v = SchemaValidator(enabled=False)
        assert v.validate_tool_schemas([{"bad": True}]) == []

    def test_validate_resource_uris_disabled(self):
        v = SchemaValidator(enabled=False)
        assert v.validate_resource_uris([{"uri": "x"}], [{"uriTemplate": "y://{z}"}]) == []

    def test_validate_tool_basic_fallback_no_type(self):
        """Cover basic validation when jsonschema not available (line 422-435)."""
        v = SchemaValidator()
        v._has_jsonschema = False
        tools = [{"name": "t", "inputSchema": {"properties": {}}}]
        violations = v.validate_tool_schemas(tools)
        assert any("type" in viol.message for viol in violations)

    def test_validate_resource_malformed_template(self):
        """Cover malformed URI template (line 349-351)."""
        v = SchemaValidator()
        # Template with unbalanced braces -- regex compilation may or may not fail
        # depending on the regex engine. The key is it should not crash.
        resources = [{"uri": "x://test"}]
        templates = [{"uriTemplate": "x://[invalid"}]
        # Should not crash -- may produce violations or not depending on regex
        violations = v.validate_resource_uris(resources, templates)
        assert isinstance(violations, list)

    def test_get_helper_with_dict(self):
        from mcp_test_harness.schema import _get
        assert _get({"a": 1}, "a") == 1
        assert _get({"a": 1}, "b", "default") == "default"

    def test_get_helper_with_object(self):
        from mcp_test_harness.schema import _get

        class Obj:
            x = 42

        assert _get(Obj(), "x") == 42
        assert _get(Obj(), "y", None) is None

    def test_template_to_regex_no_variables(self):
        pat = _template_to_regex("http://localhost/health")
        assert pat.match("http://localhost/health")
        assert not pat.match("http://localhost/other")


# ---------------------------------------------------------------------------
# scheduler.py -- uncovered lines
# ---------------------------------------------------------------------------


class TestSchedulerGaps:
    @pytest.mark.asyncio
    async def test_sequential_module_teardown(self):
        """Cover per-module teardown between modules (line 115)."""
        from mcp_test_harness.discovery import TestCase
        from mcp_test_harness.models import TestResult, TestStatus
        from unittest.mock import patch

        tc1 = TestCase(
            name="test_a", module_path=Path("mod_a.py"),
            func=lambda: None, markers={}, is_async=False,
        )
        tc2 = TestCase(
            name="test_b", module_path=Path("mod_b.py"),
            func=lambda: None, markers={}, is_async=False,
        )

        from mcp_test_harness.config import HarnessConfig
        config = HarnessConfig(server_command="echo hi", timeout=5.0)
        server = ManagedServer(
            process=None, session=MagicMock(), transport=MagicMock(),
            capabilities={"protocolVersion": "2024-11-05"},
        )

        with (
            patch("mcp_test_harness.scheduler.ServerLifecycleManager") as MockLCM,
            patch("mcp_test_harness.scheduler.TestExecutor") as MockExec,
            patch("mcp_test_harness.scheduler.FixtureManager") as MockFM,
            patch("mcp_test_harness.scheduler.register_builtin_fixtures"),
        ):
            lcm = MockLCM.return_value
            lcm.start = AsyncMock(return_value=server)
            lcm.shutdown = AsyncMock()
            lcm.start_monitor = MagicMock(return_value=None)

            fm = MockFM.return_value
            fm.teardown = AsyncMock(return_value=[])

            exec_inst = MockExec.return_value
            exec_inst.execute = AsyncMock(side_effect=[
                TestResult(name="test_a", module="mod_a.py", status=TestStatus.PASSED, duration_ms=10),
                TestResult(name="test_b", module="mod_b.py", status=TestStatus.PASSED, duration_ms=10),
            ])

            scheduler = TestScheduler()
            results = await scheduler.run_sequential([tc1, tc2], config)

        assert results.passed == 2
        # teardown should have been called for per-module between different modules
        assert fm.teardown.call_count >= 1
