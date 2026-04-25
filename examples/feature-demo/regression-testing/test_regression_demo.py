from mcp_test_harness import assert_snapshot, assert_tool_idempotent


async def test_regression_snapshot_stable(mcp_server):
    result = await mcp_server.call_tool("echo", {"text": "release-candidate"})
    assert_snapshot(result)


async def test_regression_tool_idempotent(mcp_server):
    await assert_tool_idempotent(
        mcp_server,
        "echo",
        {"text": "stable-input"},
        runs=3,
    )
