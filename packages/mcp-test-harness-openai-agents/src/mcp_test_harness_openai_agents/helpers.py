"""OpenAI Agents-specific testing helpers for MCP Test Harness.

Thin wrappers around core assertions plus MCP→OpenAI Agents schema converters.
"""

from __future__ import annotations

from typing import Any

from mcp_test_harness import assert_tool_call, MCPAssertionError


async def assert_openai_agents_tool(
    session: Any,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
    expected_text: str | None = None,
) -> Any:
    """Call an MCP tool (as used from OpenAI Agents) and optionally check text."""
    args = arguments or {}
    result = await assert_tool_call(session, tool_name, args)

    if expected_text is not None:
        content = getattr(result, "content", None) or []
        if not content:
            raise MCPAssertionError(
                f"OpenAI Agents tool '{tool_name}' returned no content"
            )
        actual_text = getattr(content[0], "text", None)
        if actual_text != expected_text:
            raise MCPAssertionError(
                f"OpenAI Agents tool '{tool_name}' text mismatch: "
                f"expected '{expected_text}', got '{actual_text}'"
            )

    return result


def mcp_tools_to_openai_agents_functions(tools: list[Any]) -> list[dict[str, Any]]:
    """Map MCP tool objects/dicts to OpenAI function-calling tool defs."""
    out: list[dict[str, Any]] = []
    for tool in tools:
        name = getattr(tool, "name", None) or tool.get("name")
        description = getattr(tool, "description", None)
        if description is None and isinstance(tool, dict):
            description = tool.get("description", "")
        schema = getattr(tool, "inputSchema", None)
        if schema is None and isinstance(tool, dict):
            schema = tool.get("inputSchema") or tool.get("input_schema") or {}
        out.append({
            "type": "function",
            "function": {
                "name": name,
                "description": description or "",
                "parameters": schema or {"type": "object", "properties": {}},
            },
        })
    return out


def create_openai_agents_test_config(
    server_command: str,
    *,
    transport: str = "stdio",
    timeout: int = 30,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build an mcp-test.yaml-shaped config for OpenAI Agents MCP testing."""
    server: dict[str, Any] = {
        "command": server_command,
        "transport": transport,
    }
    if env:
        server["env"] = env
    return {
        "server": server,
        "test": {"timeout": timeout},
    }
