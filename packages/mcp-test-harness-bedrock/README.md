# mcp-test-harness-bedrock

AWS Bedrock agents testing helpers for [MCP Test Harness](https://github.com/vaquarkhan/mcp-test-harness).

Author: Vaquar Khan -- https://github.com/vaquarkhan

## Install

```bash
pip install mcp-test-harness-bedrock
```

This automatically installs `mcp-test-harness` as a dependency.

## Usage

```python
from mcp_test_harness_bedrock import assert_bedrock_tool, mcp_tools_to_bedrock_tool_specs, create_bedrock_test_config

async def test_tool(mcp_server):
    await assert_bedrock_tool(mcp_server, "my_tool", {}, expected_text="ok")

def test_schema_bridge(mcp_tools):
    # mcp_tools from list_tools — convert for AWS Bedrock SDKs
    return mcp_tools_to_bedrock_tool_specs(mcp_tools)

cfg = create_bedrock_test_config("python server.py", timeout=45)
```

## Helpers

- Tool call assertion with optional text check
- MCP tool → AWS Bedrock schema converter
- `mcp-test.yaml`-shaped config builder

## License

Non-commercial use only with mandatory attribution. See [LICENSE](https://github.com/vaquarkhan/mcp-test-harness/blob/main/LICENSE).
