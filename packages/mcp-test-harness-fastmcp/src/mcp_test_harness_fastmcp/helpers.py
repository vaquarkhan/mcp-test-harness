"""FastMCP-specific testing helpers.

Provides convenience wrappers around mcp-test-harness assertions
tailored for FastMCP server patterns.
"""

from __future__ import annotations

from typing import Any

from mcp_test_harness import assert_tool_call, assert_resource_read, MCPAssertionError


async def assert_fastmcp_tool(
    session: Any,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
    expected_text: str | None = None,
) -> Any:
    """Call a FastMCP tool and optionally validate the text response.

    FastMCP tools typically return a single text content item.
    This helper simplifies the common pattern.

    Parameters
    ----------
    session:
        MCP ClientSession from the mcp_server fixture.
    tool_name:
        Name of the FastMCP tool to call.
    arguments:
        Arguments dict (default: empty).
    expected_text:
        If provided, checks the first content item's text matches.
    """
    args = arguments or {}
    result = await assert_tool_call(session, tool_name, args)

    if expected_text is not None:
        content = getattr(result, "content", None) or []
        if not content:
            raise MCPAssertionError(
                f"FastMCP tool '{tool_name}' returned no content"
            )
        actual_text = getattr(content[0], "text", None)
        if actual_text != expected_text:
            raise MCPAssertionError(
                f"FastMCP tool '{tool_name}' text mismatch: "
                f"expected '{expected_text}', got '{actual_text}'"
            )

    return result


async def assert_fastmcp_resource(
    session: Any,
    uri: str,
    expected_text: str | None = None,
) -> Any:
    """Read a FastMCP resource and optionally validate the text content.

    Parameters
    ----------
    session:
        MCP ClientSession from the mcp_server fixture.
    uri:
        Resource URI to read.
    expected_text:
        If provided, checks the content text matches.
    """
    return await assert_resource_read(
        session, uri, expected_content=expected_text
    )


def create_fastmcp_test_config(
    server_file: str = "server.py",
    transport: str = "stdio",
    timeout: int = 30,
) -> dict[str, Any]:
    """Create a config dict suitable for FastMCP server testing.

    Returns a dict matching the mcp-test.yaml structure.

    Parameters
    ----------
    server_file:
        Path to the FastMCP server Python file.
    transport:
        Transport type (stdio, sse, http).
    timeout:
        Per-test timeout in seconds.
    """
    return {
        "server": {
            "command": f"python {server_file}",
            "transport": transport,
        },
        "test": {
            "timeout": timeout,
        },
    }
