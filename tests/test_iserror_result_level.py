"""Regression: MCP CallToolResult.isError (spec) vs content-item isError (legacy SDKs).

FastMCP and spec-compliant servers set ``isError`` on the result object, not on
each content item.  Prior harness versions only inspected content items.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace

import pytest

from mcp_test_harness.assertions import (
    MCPAssertionError,
    _result_error_text,
    _result_is_error,
    assert_tool_call,
    assert_tool_denied,
    assert_tool_rejects,
)
from mcp_test_harness.resiliency import assert_degrades_gracefully


@dataclass
class SpecContent:
    """Content block with no per-item isError (FastMCP style)."""

    type: str = "text"
    text: str = ""


@dataclass
class SpecCallToolResult:
    """MCP CallToolResult with result-level isError."""

    content: list[SpecContent] = field(default_factory=list)
    isError: bool = False


class SpecCompliantSession:
    async def call_tool(self, name: str, arguments: dict) -> SpecCallToolResult:
        if arguments.get("fail"):
            return SpecCallToolResult(
                content=[SpecContent(text="invalid argument: missing field")],
                isError=True,
            )
        return SpecCallToolResult(
            content=[SpecContent(text="ok")],
            isError=False,
        )


@pytest.mark.asyncio
async def test_assert_tool_call_fails_on_result_level_iserror() -> None:
    """B1: error signaled only on CallToolResult must not pass assert_tool_call."""
    session = SpecCompliantSession()
    with pytest.raises(MCPAssertionError, match="returned an error"):
        await assert_tool_call(session, "echo", {"fail": True})


@pytest.mark.asyncio
async def test_assert_tool_rejects_passes_on_result_level_iserror() -> None:
    """B2: assert_tool_rejects treats result-level isError as rejection."""
    session = SpecCompliantSession()
    await assert_tool_rejects(session, "echo", {"fail": True})


@pytest.mark.asyncio
async def test_assert_tool_denied_passes_on_result_level_iserror() -> None:
    session = SpecCompliantSession()
    await assert_tool_denied(session, "echo", {"fail": True})


@pytest.mark.asyncio
async def test_assert_tool_rejects_substring_on_result_level_iserror() -> None:
    session = SpecCompliantSession()
    await assert_tool_rejects(
        session,
        "echo",
        {"fail": True},
        error_substring="invalid argument",
    )


@pytest.mark.asyncio
async def test_assert_degrades_gracefully_on_result_level_iserror() -> None:
    """B3: resiliency probe accepts spec-compliant error signaling."""
    session = SpecCompliantSession()
    await assert_degrades_gracefully(session, "echo", {"fail": True})


def test_result_is_error_detects_result_level_flag() -> None:
    result = SpecCallToolResult(
        content=[SpecContent(text="err")],
        isError=True,
    )
    assert _result_is_error(result) is True


def test_result_is_error_dict_form() -> None:
    assert _result_is_error({"isError": True, "content": [{"text": "x"}]}) is True


def test_result_error_text_falls_back_to_str_result() -> None:
    result = SpecCallToolResult(content=[], isError=True)
    assert _result_error_text(result) == str(result)


def test_result_is_error_still_checks_content_items() -> None:
    result = SimpleNamespace(
        isError=False,
        content=[SimpleNamespace(text="err", isError=True)],
    )
    assert _result_is_error(result) is True
