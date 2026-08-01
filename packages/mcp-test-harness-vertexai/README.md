# mcp-test-harness-vertexai

Google Vertex AI testing helpers for [MCP Test Harness](https://github.com/vaquarkhan/mcp-test-harness).

Author: Vaquar Khan -- https://github.com/vaquarkhan

## Install

```bash
pip install mcp-test-harness-vertexai
```

This automatically installs `mcp-test-harness` as a dependency.

## Usage

```python
from mcp_test_harness_vertexai import assert_vertexai_tool, mcp_tools_to_vertexai_function_declarations, create_vertexai_test_config

async def test_tool(mcp_server):
    await assert_vertexai_tool(mcp_server, "my_tool", {}, expected_text="ok")

def test_schema_bridge(mcp_tools):
    # mcp_tools from list_tools — convert for Google Vertex AI SDKs
    return mcp_tools_to_vertexai_function_declarations(mcp_tools)

cfg = create_vertexai_test_config("python server.py", timeout=45)
```

## Helpers

- Tool call assertion with optional text check
- MCP tool → Google Vertex AI schema converter
- `mcp-test.yaml`-shaped config builder

## License

Non-commercial use only with mandatory attribution. See [LICENSE](https://github.com/vaquarkhan/mcp-test-harness/blob/main/LICENSE).
