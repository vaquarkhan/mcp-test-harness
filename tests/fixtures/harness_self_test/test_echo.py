"""Self-test consumed by harness dogfood e2e — exercises real mcp-test CLI."""

from __future__ import annotations

from mcp_test_harness import assert_tool_call, marker


@marker(tags=["smoke", "dogfood"])
async def test_echo_tool(mcp_server) -> None:
    result = await assert_tool_call(mcp_server, "echo", {"text": "harness-e2e"})
    content = getattr(result, "content", None) or []
    assert content
