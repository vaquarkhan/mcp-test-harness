"""Cohere-specific testing helpers for MCP Test Harness.

Thin wrappers around core assertions plus MCP→Cohere schema converters.
"""

from __future__ import annotations

from typing import Any

from mcp_test_harness import assert_tool_call, MCPAssertionError


async def assert_cohere_tool(
    session: Any,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
    expected_text: str | None = None,
) -> Any:
    """Call an MCP tool (as used from Cohere) and optionally check text."""
    args = arguments or {}
    result = await assert_tool_call(session, tool_name, args)

    if expected_text is not None:
        content = getattr(result, "content", None) or []
        if not content:
            raise MCPAssertionError(
                f"Cohere tool '{tool_name}' returned no content"
            )
        actual_text = getattr(content[0], "text", None)
        if actual_text != expected_text:
            raise MCPAssertionError(
                f"Cohere tool '{tool_name}' text mismatch: "
                f"expected '{expected_text}', got '{actual_text}'"
            )

    return result


def mcp_tools_to_cohere_tools(tools: list[Any]) -> list[dict[str, Any]]:
    """Map MCP tools to Cohere tool definitions."""
    out: list[dict[str, Any]] = []
    for tool in tools:
        name = getattr(tool, "name", None) or tool.get("name")
        description = getattr(tool, "description", None)
        if description is None and isinstance(tool, dict):
            description = tool.get("description", "")
        schema = getattr(tool, "inputSchema", None)
        if schema is None and isinstance(tool, dict):
            schema = tool.get("inputSchema") or tool.get("input_schema") or {}
        props = (schema or {}).get("properties") or {}
        parameter_defs = [
            {
                "name": key,
                "description": (val or {}).get("description", ""),
                "type": (val or {}).get("type", "string"),
                "required": key in ((schema or {}).get("required") or []),
            }
            for key, val in props.items()
        ]
        out.append({
            "name": name,
            "description": description or "",
            "parameter_definitions": parameter_defs,
        })
    return out


def create_cohere_test_config(
    server_command: str,
    *,
    transport: str = "stdio",
    timeout: int = 30,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build an mcp-test.yaml-shaped config for Cohere MCP testing."""
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
