"""
Example output from `mcp-test generate` (static sample for documentation).

This file is NOT executed by pytest or mcp-test discovery in the harness repo.
Copy the patterns into your project after running generate against your server.
"""

from __future__ import annotations

from mcp_test_harness import (
    assert_tool_call,
    assert_tool_rejects,
    marker,
    skip,
)


@marker(tags=["smoke", "generated"])
async def test_tool_echo_happy_path(mcp_server) -> None:
    """Happy-path call for tool ``echo``."""
    await assert_tool_call(mcp_server, "echo", {"text": "example_text"})


@skip(reason="Generated edge case — tailor invalid payload")
@marker(tags=["generated", "edge"])
async def test_tool_echo_rejects_bad_input(mcp_server) -> None:
    """Tool ``echo`` should reject invalid input."""
    await assert_tool_rejects(mcp_server, "echo", {"__invalid__": True})


@marker(tags=["smoke", "generated"])
async def test_tool_search_happy_path(mcp_server) -> None:
    """Happy-path call for tool ``search``."""
    await assert_tool_call(mcp_server, "search", {"query": "example_query"})


@skip(reason="Generated edge case — tailor invalid payload")
@marker(tags=["generated", "edge"])
async def test_tool_search_rejects_bad_input(mcp_server) -> None:
    """Tool ``search`` should reject invalid input."""
    await assert_tool_rejects(mcp_server, "search", {"__invalid__": True})
