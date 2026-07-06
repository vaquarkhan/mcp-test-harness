"""Tests for security payload assertions."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from mcp_test_harness.assertions import MCPAssertionError
from mcp_test_harness.security_payloads import (
    _item_is_error,
    assert_injection_blocked,
    assert_no_secret_leak,
    scan_text_for_secrets,
)


@dataclass
class Content:
    text: str = ""
    isError: bool = False


@dataclass
class ToolResult:
    content: list[Content] = field(default_factory=list)


class FakeSecSession:
    def __init__(self, *, echo_payload: bool = False) -> None:
        self.echo_payload = echo_payload

    async def call_tool(self, name: str, args: dict) -> ToolResult:
        payload = args.get("input", "")
        if self.echo_payload:
            return ToolResult(content=[Content(text=str(payload))])
        return ToolResult(content=[Content(text="ok", isError=False)])


@pytest.mark.asyncio
async def test_injection_blocked_passes_on_error_response() -> None:
    session = FakeSecSession(echo_payload=False)
    await assert_injection_blocked(
        session,
        "chat",
        payloads=("test-payload",),
    )


@pytest.mark.asyncio
async def test_injection_blocked_fails_on_echo() -> None:
    session = FakeSecSession(echo_payload=True)
    with pytest.raises(MCPAssertionError, match="did not block"):
        await assert_injection_blocked(
            session,
            "chat",
            payloads=("leak-me",),
        )


@pytest.mark.asyncio
async def test_no_secret_leak() -> None:
    session = FakeSecSession()

    async def good_call(_n: str, _a: dict) -> ToolResult:
        return ToolResult(content=[Content(text="hello")])

    session.call_tool = good_call  # type: ignore[method-assign]
    await assert_no_secret_leak(session, "x", {})


def test_scan_secrets() -> None:
    hits = scan_text_for_secrets("token sk-abcdefghijklmnopqrstuvwxyz123456")
    assert hits


@pytest.mark.asyncio
async def test_no_secret_leak_fails() -> None:
    session = FakeSecSession()

    async def bad_call(_n: str, _a: dict) -> ToolResult:
        return ToolResult(content=[Content(text="key sk-abcdefghijklmnopqrstuvwxyz123456")])

    session.call_tool = bad_call  # type: ignore[method-assign]
    with pytest.raises(MCPAssertionError, match="secret pattern"):
        await assert_no_secret_leak(session, "x", {})


def test_item_is_error_attr_on_content_object() -> None:
    assert _item_is_error(Content(text="x", isError=True)) is True
