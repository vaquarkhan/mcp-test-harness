from pathlib import Path

from mcp_test_harness import (
    assert_authorization_boundary,
    assert_snapshot,
    assert_tool_idempotent,
)


async def test_eu_ai_act_protected_operation_control(mcp_server):
    await assert_authorization_boundary(
        mcp_server,
        "process_case_data",
        allowed_arguments={"role": "compliance_officer", "case_id": "EU-1001"},
        denied_arguments={"role": "guest", "case_id": "EU-1001"},
        denied_error_substring="forbidden",
    )


async def test_eu_ai_act_deterministic_decision_path(mcp_server):
    await assert_tool_idempotent(
        mcp_server,
        "echo",
        {"text": "deterministic-evidence"},
        runs=3,
    )


async def test_eu_ai_act_snapshot_traceability(mcp_server):
    result = await mcp_server.call_tool("echo", {"text": "eu-ai-act-evidence"})
    await assert_snapshot(result, "eu_ai_act_trace", test_file=Path(__file__))
