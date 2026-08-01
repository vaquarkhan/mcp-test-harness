"""MCP Test Harness helpers for DeepSeek testing."""

from __future__ import annotations

__version__ = "3.0.10"

from mcp_test_harness_deepseek.helpers import (
    assert_deepseek_tool,
    mcp_tools_to_deepseek_functions,
    create_deepseek_test_config,
)

__all__ = [
    "__version__",
    "assert_deepseek_tool",
    "mcp_tools_to_deepseek_functions",
    "create_deepseek_test_config",
]
