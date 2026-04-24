"""MCP Test Harness -- a pytest-style testing framework for MCP servers."""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "MCPAssertionError",
    "assert_capabilities",
    "assert_invalid_tool",
    "assert_latency",
    "assert_prompt",
    "assert_protocol_version",
    "assert_resource_list",
    "assert_resource_read",
    "assert_snapshot",
    "assert_tool_call",
    "assert_tool_call_validates_input",
    "assert_tool_idempotent",
    "assert_tool_list",
    "assert_tool_rejects",
    "assert_tool_schema",
    "marker",
    "skip",
]

from mcp_test_harness.assertions import (
    MCPAssertionError,
    assert_capabilities,
    assert_invalid_tool,
    assert_latency,
    assert_prompt,
    assert_protocol_version,
    assert_resource_list,
    assert_resource_read,
    assert_snapshot,
    assert_tool_call,
    assert_tool_call_validates_input,
    assert_tool_idempotent,
    assert_tool_list,
    assert_tool_rejects,
    assert_tool_schema,
)
from mcp_test_harness.discovery import marker, skip
