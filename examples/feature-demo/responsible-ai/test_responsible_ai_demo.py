from pathlib import Path

from mcp_test_harness import (
    assert_authorization_boundary,
    assert_snapshot,
    assert_tool_idempotent,
)


async def test_responsible_ai_auth_boundary(mcp_server):
    await assert_authorization_boundary(
        mcp_server,
        "transfer_funds",
        allowed_arguments={"role": "admin", "amount": 25},
        denied_arguments={"role": "guest", "amount": 25},
        denied_error_substring="forbidden",
    )


async def test_responsible_ai_deterministic_behavior(mcp_server):
    await assert_tool_idempotent(
        mcp_server,
        "echo",
        {"text": "consistent-output"},
        runs=3,
    )


async def test_responsible_ai_snapshot_auditability(mcp_server):
    result = await mcp_server.call_tool("echo", {"text": "auditable"})
    await assert_snapshot(result, "responsible_ai_echo", test_file=Path(__file__))
