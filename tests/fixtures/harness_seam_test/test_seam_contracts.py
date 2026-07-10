"""Seam tests against the rich FastMCP fixture (README contracts + coverage)."""

from __future__ import annotations

from mcp_test_harness import (
    assert_capabilities,
    assert_prompt,
    assert_resource_read,
    assert_tool_call,
    assert_tool_rejects,
    marker,
)


@marker(tags=["smoke", "seam", "contract"])
async def test_readme_assert_capabilities_subset(mcp_server) -> None:
    """Documented README pattern: empty nested dict means capability present."""
    await assert_capabilities(mcp_server, {"tools": {}})
    await assert_capabilities(mcp_server, {"tools": {}, "resources": {}, "prompts": {}})


@marker(tags=["smoke", "seam"])
async def test_echo_and_add_tools(mcp_server) -> None:
    await assert_tool_call(mcp_server, "echo", {"text": "seam"})
    await assert_tool_call(mcp_server, "add", {"a": 2, "b": 3})


@marker(tags=["smoke", "seam", "negative"])
async def test_boom_rejects(mcp_server) -> None:
    await assert_tool_rejects(mcp_server, "boom", {"reason": "expected"})


@marker(tags=["smoke", "seam"])
async def test_resource_and_prompt(mcp_server) -> None:
    await assert_resource_read(mcp_server, "seam://greeting")
    await assert_prompt(mcp_server, "welcome", {"name": "seam"})
