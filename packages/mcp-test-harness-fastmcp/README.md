# mcp-test-harness-fastmcp

FastMCP server testing helpers for [MCP Test Harness](https://github.com/vaquarkhan/mcp-test-harness).

Author: Vaquar Khan -- https://github.com/vaquarkhan

## Install

```bash
pip install mcp-test-harness-fastmcp
```

This automatically installs `mcp-test-harness` as a dependency.

## Usage

```python
from mcp_test_harness_fastmcp import assert_fastmcp_tool, assert_fastmcp_resource

async def test_echo(mcp_server):
    await assert_fastmcp_tool(mcp_server, "echo", {"message": "hi"}, expected_text="hi")

async def test_config(mcp_server):
    await assert_fastmcp_resource(mcp_server, "config://app", expected_text='{"debug": true}')
```

## License

Non-commercial use only with mandatory attribution. See [LICENSE](https://github.com/vaquarkhan/mcp-test-harness/blob/main/LICENSE).
