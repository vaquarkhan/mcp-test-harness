"""Tests for mcp_test_harness.assertions."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from mcp_test_harness.assertions import (
    MCPAssertionError,
    assert_capabilities,
    assert_prompt,
    assert_resource_read,
    assert_snapshot,
    assert_tool_call,
)


# ---------------------------------------------------------------------------
# Fake MCP SDK objects (duck-typed)
# ---------------------------------------------------------------------------


@dataclass
class FakeContent:
    text: str = ""
    isError: bool = False


@dataclass
class FakeToolResult:
    content: list[FakeContent] = field(default_factory=list)


@dataclass
class FakeResourceContent:
    text: str = ""
    mimeType: str = "text/plain"


@dataclass
class FakeResourceResult:
    contents: list[FakeResourceContent] = field(default_factory=list)


@dataclass
class FakeMessage:
    role: str = "assistant"
    content: str = ""


@dataclass
class FakePromptResult:
    messages: list[FakeMessage] = field(default_factory=list)


class FakeSession:
    """Minimal duck-typed session for testing assertion helpers."""

    def __init__(
        self,
        tool_result: FakeToolResult | None = None,
        resource_result: FakeResourceResult | None = None,
        prompt_result: FakePromptResult | None = None,
        capabilities: dict[str, Any] | None = None,
    ) -> None:
        self._tool_result = tool_result or FakeToolResult()
        self._resource_result = resource_result or FakeResourceResult()
        self._prompt_result = prompt_result or FakePromptResult()
        self.server_capabilities = capabilities

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> FakeToolResult:
        return self._tool_result

    async def read_resource(self, uri: str) -> FakeResourceResult:
        return self._resource_result

    async def get_prompt(
        self, name: str, arguments: dict[str, str] | None = None
    ) -> FakePromptResult:
        return self._prompt_result


# ---------------------------------------------------------------------------
# assert_tool_call
# ---------------------------------------------------------------------------


class TestAssertToolCall:
    def test_pass_no_expected(self) -> None:
        session = FakeSession(
            tool_result=FakeToolResult(content=[FakeContent(text="ok")])
        )
        result = asyncio.get_event_loop().run_until_complete(
            assert_tool_call(session, "my_tool", {"a": 1})
        )
        assert result.content[0].text == "ok"

    def test_pass_with_expected(self) -> None:
        session = FakeSession(
            tool_result=FakeToolResult(content=[FakeContent(text="hello")])
        )
        expected = [{"text": "hello", "isError": False}]
        asyncio.get_event_loop().run_until_complete(
            assert_tool_call(session, "t", {}, expected=expected)
        )

    def test_fail_mismatch(self) -> None:
        session = FakeSession(
            tool_result=FakeToolResult(content=[FakeContent(text="actual")])
        )
        expected = [{"text": "expected", "isError": False}]
        with pytest.raises(MCPAssertionError, match="response mismatch"):
            asyncio.get_event_loop().run_until_complete(
                assert_tool_call(session, "t", {}, expected=expected)
            )

    def test_fail_server_error(self) -> None:
        session = FakeSession(
            tool_result=FakeToolResult(
                content=[FakeContent(text="boom", isError=True)]
            )
        )
        with pytest.raises(MCPAssertionError, match="returned an error.*boom"):
            asyncio.get_event_loop().run_until_complete(
                assert_tool_call(session, "t", {})
            )

    def test_diff_in_error(self) -> None:
        session = FakeSession(
            tool_result=FakeToolResult(content=[FakeContent(text="a")])
        )
        with pytest.raises(MCPAssertionError) as exc_info:
            asyncio.get_event_loop().run_until_complete(
                assert_tool_call(session, "t", {}, expected=[{"text": "b", "isError": False}])
            )
        assert exc_info.value.diff is not None
        assert "expected" in exc_info.value.diff
        assert "actual" in exc_info.value.diff


# ---------------------------------------------------------------------------
# assert_resource_read
# ---------------------------------------------------------------------------


class TestAssertResourceRead:
    def test_pass_content(self) -> None:
        session = FakeSession(
            resource_result=FakeResourceResult(
                contents=[FakeResourceContent(text="data", mimeType="text/plain")]
            )
        )
        asyncio.get_event_loop().run_until_complete(
            assert_resource_read(session, "file:///a.txt", expected_content="data")
        )

    def test_pass_mime(self) -> None:
        session = FakeSession(
            resource_result=FakeResourceResult(
                contents=[FakeResourceContent(text="x", mimeType="application/json")]
            )
        )
        asyncio.get_event_loop().run_until_complete(
            assert_resource_read(
                session, "file:///a", expected_mime_type="application/json"
            )
        )

    def test_fail_content_mismatch(self) -> None:
        session = FakeSession(
            resource_result=FakeResourceResult(
                contents=[FakeResourceContent(text="actual")]
            )
        )
        with pytest.raises(MCPAssertionError, match="content mismatch"):
            asyncio.get_event_loop().run_until_complete(
                assert_resource_read(session, "u", expected_content="expected")
            )

    def test_fail_mime_mismatch(self) -> None:
        session = FakeSession(
            resource_result=FakeResourceResult(
                contents=[FakeResourceContent(mimeType="text/html")]
            )
        )
        with pytest.raises(MCPAssertionError, match="MIME type mismatch"):
            asyncio.get_event_loop().run_until_complete(
                assert_resource_read(session, "u", expected_mime_type="text/plain")
            )

    def test_fail_no_contents(self) -> None:
        session = FakeSession(
            resource_result=FakeResourceResult(contents=[])
        )
        with pytest.raises(MCPAssertionError, match="no content items"):
            asyncio.get_event_loop().run_until_complete(
                assert_resource_read(session, "u")
            )


# ---------------------------------------------------------------------------
# assert_prompt
# ---------------------------------------------------------------------------


class TestAssertPrompt:
    def test_pass(self) -> None:
        session = FakeSession(
            prompt_result=FakePromptResult(
                messages=[FakeMessage(role="assistant", content="hi")]
            )
        )
        expected = [{"role": "assistant", "content": "hi"}]
        asyncio.get_event_loop().run_until_complete(
            assert_prompt(session, "greet", expected_messages=expected)
        )

    def test_fail_mismatch(self) -> None:
        session = FakeSession(
            prompt_result=FakePromptResult(
                messages=[FakeMessage(role="user", content="x")]
            )
        )
        expected = [{"role": "assistant", "content": "y"}]
        with pytest.raises(MCPAssertionError, match="message structure mismatch"):
            asyncio.get_event_loop().run_until_complete(
                assert_prompt(session, "p", expected_messages=expected)
            )

    def test_no_expected_passes(self) -> None:
        session = FakeSession(
            prompt_result=FakePromptResult(messages=[FakeMessage()])
        )
        asyncio.get_event_loop().run_until_complete(
            assert_prompt(session, "p")
        )


# ---------------------------------------------------------------------------
# assert_capabilities
# ---------------------------------------------------------------------------


class TestAssertCapabilities:
    def test_pass(self) -> None:
        session = FakeSession(capabilities={"tools": True, "prompts": True})
        asyncio.get_event_loop().run_until_complete(
            assert_capabilities(session, {"tools": True})
        )

    def test_fail_missing_key(self) -> None:
        session = FakeSession(capabilities={"tools": True})
        with pytest.raises(MCPAssertionError, match="capabilities mismatch"):
            asyncio.get_event_loop().run_until_complete(
                assert_capabilities(session, {"resources": True})
            )

    def test_fail_value_mismatch(self) -> None:
        session = FakeSession(capabilities={"tools": False})
        with pytest.raises(MCPAssertionError, match="capabilities mismatch"):
            asyncio.get_event_loop().run_until_complete(
                assert_capabilities(session, {"tools": True})
            )

    def test_fail_no_capabilities(self) -> None:
        session = FakeSession()
        with pytest.raises(MCPAssertionError, match="no.*capabilities"):
            asyncio.get_event_loop().run_until_complete(
                assert_capabilities(session, {"tools": True})
            )

    def test_diff_in_error(self) -> None:
        session = FakeSession(capabilities={"tools": False})
        with pytest.raises(MCPAssertionError) as exc_info:
            asyncio.get_event_loop().run_until_complete(
                assert_capabilities(session, {"tools": True})
            )
        assert exc_info.value.diff is not None


# ---------------------------------------------------------------------------
# assert_snapshot
# ---------------------------------------------------------------------------


class TestAssertSnapshot:
    def test_creates_snapshot_when_missing(self, tmp_path: Path) -> None:
        test_file = tmp_path / "test_example.py"
        test_file.touch()
        asyncio.get_event_loop().run_until_complete(
            assert_snapshot({"key": "value"}, "my_snap", test_file)
        )
        snap = tmp_path / "__snapshots__" / "my_snap.snap"
        assert snap.exists()
        data = json.loads(snap.read_text())
        assert data == {"key": "value"}

    def test_passes_when_matches(self, tmp_path: Path) -> None:
        test_file = tmp_path / "test_example.py"
        test_file.touch()
        snap_dir = tmp_path / "__snapshots__"
        snap_dir.mkdir()
        snap = snap_dir / "s.snap"
        snap.write_text(json.dumps({"a": 1}, indent=2, sort_keys=True) + "\n")
        asyncio.get_event_loop().run_until_complete(
            assert_snapshot({"a": 1}, "s", test_file)
        )

    def test_fails_on_mismatch(self, tmp_path: Path) -> None:
        test_file = tmp_path / "test_example.py"
        test_file.touch()
        snap_dir = tmp_path / "__snapshots__"
        snap_dir.mkdir()
        snap = snap_dir / "s.snap"
        snap.write_text(json.dumps({"a": 1}, indent=2, sort_keys=True) + "\n")
        with pytest.raises(MCPAssertionError, match="Snapshot mismatch"):
            asyncio.get_event_loop().run_until_complete(
                assert_snapshot({"a": 2}, "s", test_file)
            )

    def test_update_overwrites(self, tmp_path: Path) -> None:
        test_file = tmp_path / "test_example.py"
        test_file.touch()
        snap_dir = tmp_path / "__snapshots__"
        snap_dir.mkdir()
        snap = snap_dir / "s.snap"
        snap.write_text(json.dumps({"old": True}, indent=2, sort_keys=True) + "\n")
        asyncio.get_event_loop().run_until_complete(
            assert_snapshot({"new": True}, "s", test_file, update=True)
        )
        data = json.loads(snap.read_text())
        assert data == {"new": True}
