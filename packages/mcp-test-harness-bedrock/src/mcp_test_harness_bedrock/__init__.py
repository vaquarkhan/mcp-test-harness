"""MCP Test Harness helpers for AWS Bedrock testing."""

from __future__ import annotations

__version__ = "3.0.10"

from mcp_test_harness_bedrock.helpers import (
    assert_bedrock_tool,
    mcp_tools_to_bedrock_tool_specs,
    create_bedrock_test_config,
)

__all__ = [
    "__version__",
    "assert_bedrock_tool",
    "mcp_tools_to_bedrock_tool_specs",
    "create_bedrock_test_config",
]
