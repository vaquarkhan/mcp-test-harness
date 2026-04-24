# MCP assertions — one demo for every `assert_*` helper

All helpers below are exercised in **[assertions_async_demo.py](assertions_async_demo.py)** (no real server; duck-typed fake session). Run: `python examples/assertions_async_demo.py`

| `assert_*` | Where in the demo (each step prints e.g. `1) assert_tool_call`) |
|------------|-----------------------------------------------------|
| `assert_tool_call` | step 1 |
| `assert_resource_read` | step 2 (exact `expected_content` + `expected_mime_type`) |
| `assert_prompt` | step 3 |
| `assert_capabilities` | step 4 |
| `assert_tool_list` | step 5 |
| `assert_resource_list` | step 5 |
| `assert_tool_rejects` | step 6 |
| `assert_invalid_tool` | step 7 |
| `assert_tool_schema` | step 8 |
| `assert_protocol_version` | step 9 |
| `assert_tool_idempotent` | step 10 |
| `assert_tool_call_validates_input` | step 11 |
| `assert_latency` | step 12 |
| `assert_snapshot` | step 13 |

**Deeper API notes:** [DEVELOPER_GUIDE.md – assertions](../docs/DEVELOPER_GUIDE.md) · latency & markers: [PERFORMANCE.md](../docs/PERFORMANCE.md)
