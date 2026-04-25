"""Feature demo scenario test.

Update placeholder tool/resource/prompt names for your MCP server.
Run with:
    mcp-test --server-command "python -m your_server" examples/feature-demo/python-scenarios
"""
from __future__ import annotations

from pathlib import Path

from mcp_test_harness import (
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
    marker,
    skip,
)

@marker(tags=["perf"])
async def test_demo_18_assert_latency_p95(mcp_server):
    await assert_latency(
        mcp_server, "echo", {"text": "p95"}, max_ms=800.0, runs=20, aggregate="p95"
    )
