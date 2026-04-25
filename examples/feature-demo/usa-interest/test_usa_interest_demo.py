from mcp_test_harness import (
    assert_authorization_boundary,
    assert_capabilities,
    assert_tool_denied,
)


async def test_usa_interest_confused_deputy_guard(mcp_server):
    await assert_authorization_boundary(
        mcp_server,
        "kafka_publish",
        allowed_arguments={"role": "topic_admin", "topic": "ops.audit", "value": "ok"},
        denied_arguments={"role": "viewer", "topic": "ops.audit", "value": "blocked"},
        denied_error_substring="forbidden",
    )


async def test_usa_interest_least_privilege_denied_write(mcp_server):
    await assert_tool_denied(
        mcp_server,
        "kafka_publish",
        {"role": "readonly", "topic": "finance.txn", "value": "deny"},
        error_substring="forbidden",
    )


async def test_usa_interest_capability_contract(mcp_server):
    await assert_capabilities(mcp_server, {"tools": {}})
