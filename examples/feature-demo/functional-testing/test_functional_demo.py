from mcp_test_harness import (
    assert_capabilities,
    assert_prompt,
    assert_resource_read,
    assert_tool_call,
    assert_tool_schema,
)


async def test_functional_tool_call_smoke(mcp_server):
    await assert_tool_call(mcp_server, "echo", {"text": "hello"})


async def test_functional_contract_smoke(mcp_server):
    await assert_capabilities(mcp_server, {"tools": {}})
    await assert_tool_schema(mcp_server, "echo", {"type": "object"})
    await assert_resource_read(mcp_server, "resource://status")
    await assert_prompt(mcp_server, "summarize")
