# Fixture system (built-ins + plugin)

**Built-in (always available in tests):**
- **`mcp_server`** — new MCP client session per test (per-test)
- **`mcp_server_session`** — one session per **module** (per-module)

```python
async def test_uses_session(mcp_server):
    from mcp_test_harness.assertions import assert_tool_list
    await assert_tool_list(mcp_server, expected_tools=["echo"])
```

**Custom fixtures in CI:** the recommended extension path is a **plugin** that calls `context.add_fixture(...)` — see the complete **`test_config`** / **`custom_greeting_assertion`** pattern in [reference_plugin.py](reference_plugin.py). That matches how the scheduler registers fixtures for each run.

**Related:** [DEVELOPER_GUIDE – fixtures](../docs/DEVELOPER_GUIDE.md#part-4-fixtures)
