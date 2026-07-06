"""Resiliency assertions for MCP sessions under error and recovery."""

from __future__ import annotations

from typing import Any

from mcp_test_harness.assertions import MCPAssertionError, _result_is_error


def _content_is_error(result: Any) -> bool:
    return _result_is_error(result)


async def assert_degrades_gracefully(
    session: Any,
    tool_name: str,
    bad_arguments: dict[str, Any],
) -> None:
    """Invalid input must return an MCP tool error, not break the transport."""
    result = await session.call_tool(tool_name, bad_arguments)
    if not _content_is_error(result):
        raise MCPAssertionError(
            f"Tool '{tool_name}' accepted bad arguments without isError response",
        )


async def assert_reconnects(
    session: Any,
    tool_name: str,
    valid_arguments: dict[str, Any],
    *,
    probe_errors: int = 3,
) -> None:
    """Session remains usable after a burst of failing tool calls."""
    for _ in range(max(1, probe_errors)):
        try:
            await session.call_tool(tool_name, {"__mcp_harness_probe_invalid__": True})
        except Exception:
            pass
    await session.list_tools()
    result = await session.call_tool(tool_name, valid_arguments)
    if _content_is_error(result):
        raise MCPAssertionError(
            f"Tool '{tool_name}' still returns error after recovery probe",
        )


async def assert_survives_crash(
    session: Any,
    tool_name: str,
    valid_arguments: dict[str, Any],
    *,
    error_arguments: dict[str, Any] | None = None,
    error_burst: int = 5,
) -> None:
    """After repeated tool-level failures, valid calls still succeed.

    This checks **server resilience** (errors do not poison the session).
    It does not kill the server process; use integration tests with process
    supervision for hard-crash scenarios.
    """
    bad = error_arguments or {"__mcp_harness_error_burst__": True}
    for _ in range(max(1, error_burst)):
        try:
            await session.call_tool(tool_name, bad)
        except Exception:
            pass
    result = await session.call_tool(tool_name, valid_arguments)
    if _content_is_error(result):
        raise MCPAssertionError(
            f"Tool '{tool_name}' unavailable after error burst — session may be poisoned",
        )
