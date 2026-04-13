# MCP Test Harness

**Automated Testing Framework for Model Context Protocol (MCP) Servers**

Author: [Vaquar Khan](https://github.com/vaquarkhan)

MCP Test Harness is a pytest-style testing framework for [MCP](https://modelcontextprotocol.io/) servers. It provides the `mcp-test` CLI to discover, run, and report on tests automatically -- replacing manual validation through the MCP Inspector.

No existing tool lets you programmatically test MCP servers in CI/CD pipelines. MCP Test Harness fills that gap.

For the complete API reference, see [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md).

For production security (prompt injection defense, PII redaction, rate limiting, RBAC), see [MCP-Bastion](https://github.com/vaquarkhan/MCP-Bastion) -- the companion security middleware project.

## Core Features

| Feature | Description |
|---------|-------------|
| Test discovery | Finds `test_*.py` files and `test_` functions automatically (pytest conventions) |
| MCP assertions | `assert_tool_call`, `assert_resource_read`, `assert_prompt`, `assert_capabilities`, `assert_snapshot` |
| Fixture system | Built-in `mcp_server` fixture with per-test and per-module scoping, custom fixtures via decorator |
| Schema validation | Validates every JSON-RPC response against the MCP specification automatically |
| Snapshot testing | Capture and compare server responses for regression detection |
| Parallel execution | Run tests across multiple workers, each with its own server instance |
| Markers | `@marker(timeout=60, retry=3, tags=["smoke"])` and `@skip(reason="...")` |
| Reports | Console summary, JUnit XML (GitHub Actions/Jenkins/GitLab), JSON with full metadata |
| Plugin system | Extend with custom assertions, fixtures, reporters, and transport adapters |
| Transport support | stdio, SSE, streamable HTTP -- test local and remote servers |
| GitHub Action | One-line CI integration with artifact upload |
| Standalone binary | Single binary via PyInstaller, no Python required on target |

## Why MCP Test Harness (vs MCP Inspector)

| | MCP Inspector | MCP Test Harness |
|---|---|---|
| Execution | Manual, browser-based clicking | Automated CLI, runs in CI |
| CI/CD integration | Not possible | Native (exit codes, JUnit XML, GitHub Action) |
| Regression detection | Manual re-testing | Snapshot testing, automated on every commit |
| Schema validation | Manual visual check | Automatic on every response |
| Parallel testing | No | Yes, with per-worker server isolation |
| Reporting | Visual only | Console, JSON, JUnit XML |
| Extensibility | None | Plugin system for custom rules |

## Installation

```bash
pip install mcplint
```

Or from source:

```bash
git clone https://github.com/vaquarkhan/mcp-test-harness.git
cd mcp-test-harness
python -m venv .venv && source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"
mcp-test --version
```

## Quick Start

### 1. Write a test

Create `tests/test_my_server.py`:

```python
from mcp_test_harness import assert_tool_call, assert_capabilities

async def test_server_has_tools(mcp_server):
    """Verify the server advertises tool capabilities."""
    await assert_capabilities(mcp_server, {"tools": {}})

async def test_echo_tool(mcp_server):
    """Call the echo tool and check it works."""
    result = await assert_tool_call(mcp_server, "echo", {"message": "hello"})
    assert result is not None
```

The `mcp_server` parameter is a built-in fixture. The harness automatically starts your server, connects via MCP, performs the initialize handshake, and injects a ready-to-use session.

### 2. Run it

```bash
mcp-test --server-command "python my_server.py" tests/
```

Output:

```
  [PASS] test_server_has_tools (45.2ms)
  [PASS] test_echo_tool (120.8ms)

2 passed, 0 failed, 0 errored, 0 skipped
Total time: 312.5ms
```

### 3. Add a config file

Create `mcp-test.yaml`:

```yaml
server:
  command: python my_server.py
  transport: stdio

test:
  dirs: [tests/]
  timeout: 30

report:
  format: junit
  output: reports/results.xml
```

Then just: `mcp-test`

## Assertion Reference

### assert_tool_call -- invoke a tool and validate the response

```python
# Basic: fail if the tool returns an error
await assert_tool_call(mcp_server, "echo", {"message": "hello"})

# With expected output
await assert_tool_call(mcp_server, "add", {"a": 1, "b": 2},
    expected=[{"text": "3", "isError": False}])

# Use the return value
result = await assert_tool_call(mcp_server, "get_data", {})
assert len(result.content) > 0
```

### assert_resource_read -- read a resource and check content/MIME type

```python
await assert_resource_read(mcp_server, "file:///config.json",
    expected_content='{"debug": true}',
    expected_mime_type="application/json")
```

### assert_prompt -- get a prompt and validate messages

```python
await assert_prompt(mcp_server, "summarize",
    arguments={"text": "The quick brown fox."},
    expected_messages=[{"role": "assistant", "content": "Summary: A fox."}])
```

### assert_capabilities -- verify server capabilities

```python
await assert_capabilities(mcp_server, {"tools": {}, "resources": {}})
```

### assert_snapshot -- regression detection via stored snapshots

```python
from pathlib import Path
from mcp_test_harness import assert_snapshot

async def test_stable_output(mcp_server):
    result = await mcp_server.call_tool("generate_report", {})
    await assert_snapshot(result, "report_output", test_file=Path(__file__))
```

First run creates the snapshot. Later runs compare against it. Update with `mcp-test --update-snapshots`.

All assertions produce diff output on failure:

```
  [FAIL] test_echo (18.5ms)
      Tool 'echo' response mismatch
      --- expected
      +++ actual
      @@ -1,3 +1,3 @@
       [
      -  {"text": "hello", "isError": false}
      +  {"text": "HELLO", "isError": false}
       ]
```

## Fixtures

Built-in fixtures:

| Fixture | Scope | Description |
|---------|-------|-------------|
| `mcp_server` | Per-test | Fresh MCP session for each test |
| `mcp_server_session` | Per-module | Shared session across all tests in a file |

Custom fixtures:

```python
from mcp_test_harness.fixtures import fixture, FixtureScope

@fixture
async def api_key():
    return "test-key-12345"

@fixture
async def database():
    db = await connect()
    yield db              # test runs here
    await db.close()      # teardown

@fixture(scope=FixtureScope.PER_MODULE)
async def shared_client():
    client = await create_client()
    yield client
    await client.close()

# Injected by parameter name
async def test_query(mcp_server, database, api_key):
    result = await mcp_server.call_tool("query", {"db": database.url, "key": api_key})
```

## Markers

```python
from mcp_test_harness import marker, skip

@marker(timeout=120)                    # custom timeout
@marker(retry=3)                        # retry on failure
@marker(tags=["smoke", "critical"])     # tags for filtering
@marker(timeout=60, retry=2, tags=["integration"])  # combine

@skip                                   # skip unconditionally
@skip(reason="Bug #42")                # skip with reason
```

Filter from CLI:

```bash
mcp-test -m smoke           # run only smoke-tagged tests
mcp-test -k "test_echo"     # run tests matching name
mcp-test -k "*workflow*"    # glob patterns
```

## Reports

```bash
# JUnit XML for CI (GitHub Actions, Jenkins, GitLab)
mcp-test --report-format junit --report-output results.xml

# JSON with full metadata (server capabilities, retry history, schema violations)
mcp-test --report-format json --report-output results.json
```

Console output is always printed:

```
  [PASS] test_echo (45.2ms)
  [FAIL] test_divide (18.5ms)
      Division by zero
  [SKIP] test_future (0.0ms)

2 passed, 1 failed, 0 errored, 1 skipped
Total time: 200.0ms
```

## Parallel Execution

```bash
mcp-test --parallel              # use all CPU cores
mcp-test --parallel --workers 4  # specify worker count
```

Each worker gets its own server instance. If one crashes, others continue.

## Transport Support

| Transport | Use case | Example |
|-----------|----------|---------|
| stdio | Local servers (default) | `--server-command "python server.py"` |
| SSE | Remote servers via Server-Sent Events | `--transport sse --server-command "http://localhost:8080/sse"` |
| HTTP | Remote servers via streamable HTTP | `--transport http --server-command "http://localhost:8080/mcp"` |

With authentication:

```yaml
server:
  command: http://your-server.example.com/mcp
  transport: http
  transport_options:
    headers:
      Authorization: "Bearer your-token"
```

## GitHub Action

```yaml
# .github/workflows/mcp-tests.yml
name: MCP Server Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Test MCP Server
        uses: vaquarkhan/mcp-test-harness/.github/actions/mcp-test@main
        with:
          server-command: "python my_server.py"
          test-directory: "tests/"
          report-format: "junit"
```

| Input | Default | Description |
|-------|---------|-------------|
| `server-command` | `""` | Command to start the server |
| `transport` | `stdio` | stdio, sse, or http |
| `test-directory` | `tests/` | Path to test files |
| `config-file` | `""` | Path to config file |
| `report-format` | `junit` | json or junit |
| `harness-version` | `latest` | Version to install |

## Plugins

Extend MCP Test Harness with custom assertions, fixtures, reporters, and transports:

```python
from mcp_test_harness.plugins import PluginContext
from mcp_test_harness.fixtures import FixtureScope

class MyPlugin:
    name = "my-plugin"

    def register(self, context: PluginContext) -> None:
        context.add_assertion("assert_latency", check_latency)
        context.add_fixture("db", db_factory, FixtureScope.PER_MODULE)
        context.add_reporter("markdown", MarkdownReporter())

plugin = MyPlugin()
```

Load via config:

```yaml
plugins:
  - my_plugin.py
  - my_package.plugin_module
```

Or via Python entry points (auto-discovered):

```toml
[project.entry-points.mcp_test_harness]
my-plugin = "my_package.plugin:plugin"
```

See [examples/reference_plugin.py](examples/reference_plugin.py) for a complete example.

## Standalone Binary

```bash
pip install -e ".[dev]"
python scripts/build_binary.py
dist/mcp-test --version
```

No Python required on the target machine. Cross-platform: Linux, macOS, Windows.

## Security Testing with MCP-Bastion

MCP Test Harness tests that your MCP server works correctly. For production security, pair it with [MCP-Bastion](https://github.com/vaquarkhan/MCP-Bastion) -- an active defense middleware that protects MCP servers at runtime.

| Concern | Tool | What it does |
|---------|------|-------------|
| Functional testing | **MCP Test Harness** | Automated tests for tools, resources, prompts, capabilities |
| Prompt injection defense | [MCP-Bastion](https://github.com/vaquarkhan/MCP-Bastion) | Blocks jailbreaks via Meta PromptGuard (local, under 5ms) |
| PII redaction | [MCP-Bastion](https://github.com/vaquarkhan/MCP-Bastion) | Masks SSN, email, phone via Microsoft Presidio |
| Rate limiting | [MCP-Bastion](https://github.com/vaquarkhan/MCP-Bastion) | Token budgets, iteration caps, denial-of-wallet protection |
| RBAC | [MCP-Bastion](https://github.com/vaquarkhan/MCP-Bastion) | Tool-level permissions by role |
| Schema validation | **MCP Test Harness** | Validates JSON-RPC responses against MCP spec |
| Regression detection | **MCP Test Harness** | Snapshot testing catches unintended changes |
| Audit logging | [MCP-Bastion](https://github.com/vaquarkhan/MCP-Bastion) | Logs who, what, when, blocked/allowed |

Use both together for a complete MCP server development workflow:

```bash
# Test your server
mcp-test --server-command "python my_server.py" tests/

# Secure your server
pip install mcp-bastion-python
```

```python
# In your server code
from mcp_bastion import MCPBastionMiddleware

bastion = MCPBastionMiddleware(
    enable_prompt_guard=True,
    enable_pii_redaction=True,
    enable_rate_limit=True,
)
```

MCP-Bastion supports 16+ framework integrations including FastMCP, LangChain, OpenAI, Anthropic, AWS Bedrock, and more. See the [MCP-Bastion README](https://github.com/vaquarkhan/MCP-Bastion) for full docs.

## Dependency Management (mcplint shim)

The `mcplint` sub-package pins MCP-Bastion versions and provides helpers:

```python
from mcplint import bastion_version, bedrock_version

print(bastion_version())    # e.g. "1.0.12"
print(bedrock_version())    # None if bedrock extra not installed
```

Verify: `python scripts/verify_upstream.py`

## CLI Reference

```
mcp-test [TEST_PATH] [OPTIONS]

  --server-command CMD     Command to start the MCP server
  --transport TYPE         stdio | sse | http (default: stdio)
  --config PATH            Path to mcp-test.yaml or mcp-test.toml
  --timeout SECONDS        Per-test timeout (default: 30)
  --parallel               Run tests in parallel
  --workers N              Parallel worker count (default: CPU count)
  -k PATTERN               Filter by test name
  -m MARKER                Filter by marker/tag
  --report-format FORMAT   json | junit
  --report-output PATH     Report file path
  --verbose                Full server communication logs
  --update-snapshots       Overwrite stored snapshots
  --version                Print version
```

Exit codes: `0` = passed, `1` = failures, `2` = config error

## Configuration Reference

```yaml
server:
  command: python my_server.py       # required
  transport: stdio                   # stdio | sse | http
  transport_options: {}              # host, port, headers, etc.

test:
  dirs: [tests/]                     # directories to search
  timeout: 30                        # per-test timeout (seconds)
  parallel: false                    # run in parallel
  workers: 4                         # parallel worker count

report:
  format: junit                      # json | junit
  output: reports/results.xml        # output file path

schema_validation: true              # validate JSON-RPC responses
plugins: []                          # plugin paths or module names
redact_patterns: []                  # regex patterns to redact from verbose output
```

## Project Structure

```
mcp-test-harness/
+-- pyproject.toml
+-- mcp_test_harness.spec           # PyInstaller config
+-- src/
|   +-- mcplint/                    # dependency shim
|   +-- mcp_test_harness/           # test framework (14 modules)
|       +-- cli.py                  # mcp-test entry point
|       +-- config.py               # YAML/TOML config loading
|       +-- discovery.py            # test file/function discovery
|       +-- executor.py             # test execution, timeout, retry
|       +-- scheduler.py            # sequential + parallel scheduling
|       +-- lifecycle.py            # server start/stop/monitor
|       +-- transport.py            # stdio, SSE, HTTP adapters
|       +-- assertions.py           # 5 built-in assertions
|       +-- schema.py               # JSON-RPC / MCP schema validation
|       +-- fixtures.py             # fixture manager
|       +-- plugins.py              # plugin registry
|       +-- reporting.py            # console, JSON, JUnit reporters
|       +-- snapshots.py            # snapshot testing
|       +-- parser.py               # JSON-RPC message parser
|       +-- models.py               # shared data models
+-- examples/
|   +-- basic_usage.py
|   +-- version_gate.py
|   +-- reference_plugin.py         # complete plugin example
+-- scripts/
|   +-- verify_upstream.py
|   +-- build_binary.py
+-- tests/                          # 370 tests, 96% coverage
+-- docs/
|   +-- DEVELOPER_GUIDE.md          # complete API and integration guide
|   +-- TUTORIAL.md                 # step-by-step tutorial
|   +-- DECISIONS.md                # architecture decisions
+-- .github/
    +-- actions/mcp-test/           # reusable GitHub Action
    +-- workflows/validate.yml      # CI pipeline
```

## Testing

```bash
# Run all MCP Test Harness tests
python -m pytest tests/ -q

# Quick offline check (no heavy deps)
python -m pytest tests/test_pyproject.py -q

# With coverage
python -m coverage run -m pytest tests/ -q
python -m coverage report --show-missing
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `mcp-test: command not found` | Run `pip install -e ".[dev]"` |
| Tests hang | Check `--timeout`; server may not respond to MCP handshake |
| `No tests discovered` | Files must match `test_*.py` or `*_test.py`; functions must start with `test_` |
| Snapshot mismatch | Run `mcp-test --update-snapshots` after intentional changes |
| Server crashes during tests | Check server logs; harness marks remaining tests as errored |
| Config file not found | Harness looks for `mcp-test.yaml` / `mcp-test.toml` in cwd, or use `--config` |

## Framework Integration Packages

MCP Test Harness provides framework-specific testing helpers. Each package auto-installs `mcplint` as a dependency:

| Package | Tests for | Install |
|---------|-----------|---------|
| `mcplint` | Any MCP server (core) | `pip install mcplint` |
| `mcplint-fastmcp` | FastMCP servers | `pip install mcplint-fastmcp` |
| `mcplint-langchain` | LangChain MCP tools | `pip install mcplint-langchain` |
| `mcplint-openai` | OpenAI function calling | `pip install mcplint-openai` |
| `mcplint-anthropic` | Anthropic Claude tool use | `pip install mcplint-anthropic` |
| `mcplint-bedrock` | AWS Bedrock agents | `pip install mcplint-bedrock` |
| `mcplint-gemini` | Google Gemini | `pip install mcplint-gemini` |
| `mcplint-crewai` | CrewAI agents | `pip install mcplint-crewai` |
| `mcplint-llamaindex` | LlamaIndex tools | `pip install mcplint-llamaindex` |
| `mcplint-groq` | Groq inference | `pip install mcplint-groq` |
| `mcplint-mistral` | Mistral AI | `pip install mcplint-mistral` |
| `mcplint-cohere` | Cohere | `pip install mcplint-cohere` |
| `mcplint-azure` | Azure OpenAI | `pip install mcplint-azure` |
| `mcplint-vertexai` | Google Vertex AI | `pip install mcplint-vertexai` |
| `mcplint-huggingface` | Hugging Face Inference | `pip install mcplint-huggingface` |
| `mcplint-deepseek` | DeepSeek AI | `pip install mcplint-deepseek` |
| `mcplint-together` | Together AI | `pip install mcplint-together` |
| `mcplint-fireworks` | Fireworks AI | `pip install mcplint-fireworks` |

## Related Projects

| Project | Purpose |
|---------|---------|
| [MCP-Bastion](https://github.com/vaquarkhan/MCP-Bastion) | Security middleware for MCP servers (prompt injection, PII, rate limiting, RBAC) |
| [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) | Official Python SDK for building MCP servers and clients |
| [MCP Inspector](https://github.com/modelcontextprotocol/inspector) | Visual debugging tool for MCP servers (manual, browser-based) |

## License

Non-commercial use only with mandatory attribution.

Author: Vaquar Khan -- https://github.com/vaquarkhan

See [LICENSE](LICENSE) for full terms. Contact the author for commercial licensing.
