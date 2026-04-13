# mcp-test-harness-openai

OpenAI function calling testing helpers for [MCP Test Harness](https://github.com/vaquarkhan/mcp-test-harness).

Author: Vaquar Khan -- https://github.com/vaquarkhan

## Install

```bash
pip install mcp-test-harness-openai
```

This automatically installs `mcp-test-harness` as a dependency.

## Usage

```python
from mcp_test_harness import assert_tool_call, assert_capabilities

async def test_server(mcp_server):
    await assert_capabilities(mcp_server, {"tools": {}})
    await assert_tool_call(mcp_server, "my_tool", {})
```

## License

Non-commercial use only with mandatory attribution. See [LICENSE](https://github.com/vaquarkhan/mcp-test-harness/blob/main/LICENSE).
