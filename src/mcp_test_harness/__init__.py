"""MCP Test Harness -- a pytest-style testing framework for MCP servers."""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "MCPAssertionError",
    "assert_capabilities",
    "assert_prompt",
    "assert_resource_read",
    "assert_snapshot",
    "assert_tool_call",
    "marker",
    "skip",
]

from mcp_test_harness.assertions import (
    MCPAssertionError,
    assert_capabilities,
    assert_prompt,
    assert_resource_read,
    assert_snapshot,
    assert_tool_call,
)
from mcp_test_harness.discovery import marker, skip
