"""MCP Test Harness -- a pytest-style testing framework for MCP servers."""

from __future__ import annotations

__version__ = "2.4.0"

__all__ = [
    "__version__",
    "MCPAssertionError",
    "assert_capabilities",
    "assert_authorization_boundary",
    "assert_degrades_gracefully",
    "assert_injection_blocked",
    "assert_invalid_tool",
    "assert_latency",
    "assert_latency_within_baseline",
    "assert_no_secret_leak",
    "assert_path_traversal_blocked",
    "assert_prompt",
    "assert_protocol_version",
    "assert_reconnects",
    "assert_resource_list",
    "assert_resource_read",
    "assert_snapshot",
    "assert_survives_crash",
    "assert_throughput",
    "assert_tool_call",
    "assert_tool_call_validates_input",
    "assert_tool_denied",
    "assert_tool_idempotent",
    "assert_tool_list",
    "assert_tool_rejects",
    "assert_tool_schema",
    "coverage_to_dict",
    "marker",
    "run_security_payload_pack",
    "save_baseline",
    "skip",
]

from mcp_test_harness.assertions import (
    MCPAssertionError,
    assert_capabilities,
    assert_authorization_boundary,
    assert_invalid_tool,
    assert_latency,
    assert_throughput,
    assert_prompt,
    assert_protocol_version,
    assert_resource_list,
    assert_resource_read,
    assert_snapshot,
    assert_tool_call,
    assert_tool_call_validates_input,
    assert_tool_denied,
    assert_tool_idempotent,
    assert_tool_list,
    assert_tool_rejects,
    assert_tool_schema,
)
from mcp_test_harness.discovery import marker, skip
from mcp_test_harness.baselines import assert_latency_within_baseline, save_baseline
from mcp_test_harness.coverage import coverage_to_dict
from mcp_test_harness.resiliency import (
    assert_degrades_gracefully,
    assert_reconnects,
    assert_survives_crash,
)
from mcp_test_harness.security_payloads import (
    assert_injection_blocked,
    assert_no_secret_leak,
    assert_path_traversal_blocked,
    run_security_payload_pack,
)
