# mcp-test-harness-openai-agents

OpenAI Agents SDK testing helpers for [MCP Test Harness](https://github.com/vaquarkhan/mcp-test-harness).

Author: Vaquar Khan -- https://github.com/vaquarkhan

## Install

```bash
pip install mcp-test-harness-openai-agents
```

This automatically installs `mcp-test-harness` as a dependency.

## Usage

```python
from mcp_test_harness_openai_agents import assert_openai_agents_tool, mcp_tools_to_openai_agents_functions, create_openai_agents_test_config

async def test_tool(mcp_server):
    await assert_openai_agents_tool(mcp_server, "my_tool", {}, expected_text="ok")

def test_schema_bridge(mcp_tools):
    # mcp_tools from list_tools — convert for OpenAI Agents SDKs
    return mcp_tools_to_openai_agents_functions(mcp_tools)

cfg = create_openai_agents_test_config("python server.py", timeout=45)
```

## Helpers

- Tool call assertion with optional text check
- MCP tool → OpenAI Agents schema converter
- `mcp-test.yaml`-shaped config builder

## License

Non-commercial use only with mandatory attribution. See [LICENSE](https://github.com/vaquarkhan/mcp-test-harness/blob/main/LICENSE).
