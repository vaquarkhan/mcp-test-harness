# MCPLint

Author: Vaquar Khan -- https://github.com/vaquarkhan

MCPLint is a pytest-style testing framework and developer toolkit for [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) servers. It provides the `mcp-test` CLI to write and run automated tests against any MCP server, replacing manual validation through the MCP Inspector.

No existing tool lets you programmatically test MCP servers in CI pipelines. MCPLint fills that gap.

For the complete API reference and integration guide, see [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md).

---

## Table of contents

- [What MCPLint does](#what-mcplint-does)
- [Installation](#installation)
- [Quick start -- write and run your first test](#quick-start----write-and-run-your-first-test)
- [Configuration file](#configuration-file)
- [All five assertion types](#all-five-assertion-types)
- [Fixtures -- setup and teardown](#fixtures----setup-and-teardown)
- [Markers -- timeout, retry, skip, tags](#markers----timeout-retry-skip-tags)
- [Snapshot testing](#snapshot-testing)
- [Schema validation](#schema-validation)
- [Reports for CI](#reports-for-ci)
- [Parallel execution](#parallel-execution)
- [Testing remote servers (SSE and HTTP)](#testing-remote-servers-sse-and-http)
- [GitHub Action](#github-action)
- [Plugins](#plugins)
- [Standalone binary](#standalone-binary)
- [Dependency management (mcplint shim)](#dependency-management-mcplint-shim)
- [CLI reference](#cli-reference)
- [Configuration file reference](#configuration-file-reference)
- [Project layout](#project-layout)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## What MCPLint does

MCPLint is two things in one package:

1. **MCP Test Harness** (`mcp-test` CLI) -- a pytest-style framework for automated testing of MCP servers. Write async test functions, use built-in assertions for tool calls, resource reads, prompts, and capabilities. Get JUnit/JSON reports for CI. Run tests in parallel. Extend with plugins.

2. **Dependency shim** (`mcplint` package) -- pins and verifies MCP ecosystem dependencies so your team has a consistent install. If you need security middleware for your MCP server in production, MCPLint can optionally pull in [MCP-Bastion](https://github.com/vaquarkhan/MCP-Bastion) as a dependency.

The test harness is the core of this project. Everything else supports it.

---

## Installation

```bash
git clone <your-repo-url>/MCPLint.git
cd MCPLint

python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install --upgrade pip
pip install -e ".[dev]"
```

Verify:

```bash
mcp-test --version
```

---

## Quick start -- write and run your first test

Create `tests/test_my_server.py`:

```python
"""Tests for my MCP server."""

from mcp_test_harness import assert_tool_call, assert_capabilities


async def test_server_advertises_tools(mcp_server):
    """The server should declare tool capabilities during the MCP handshake."""
    await assert_capabilities(mcp_server, {"tools": {}})


async def test_echo_tool_works(mcp_server):
    """The echo tool should return the input message without errors."""
    result = await assert_tool_call(
        mcp_server,
        "echo",
        {"message": "hello world"},
    )
    assert result is not None
```

The `mcp_server` parameter is a built-in fixture. The harness automatically:
1. Starts your MCP server using the command you provide
2. Connects via the MCP protocol (stdio, SSE, or HTTP)
3. Performs the MCP initialize handshake
4. Injects a ready-to-use ClientSession into your test function
5. Shuts down the server when tests finish

Run it:

```bash
mcp-test --server-command "python my_server.py" tests/
```

Output:

```
  [PASS] test_server_advertises_tools (45.2ms)
  [PASS] test_echo_tool_works (120.8ms)

2 passed, 0 failed, 0 errored, 0 skipped
Total time: 312.5ms
```

If a test fails, you get a diff showing expected vs actual:

```
  [FAIL] test_echo_tool_works (18.5ms)
      Tool 'echo' response mismatch
      --- expected
      +++ actual
      @@ -1,3 +1,3 @@
       [
      -  {"text": "hello world", "isError": false}
      +  {"text": "HELLO WORLD", "isError": false}
       ]
```

---

## Configuration file

Instead of passing flags every time, create `mcp-test.yaml`:

```yaml
server:
  command: python my_server.py
  transport: stdio

test:
  dirs:
    - tests/
  timeout: 30

report:
  format: junit
  output: reports/results.xml

schema_validation: true

redact_patterns:
  - "sk-[a-zA-Z0-9]+"
  - "Bearer [a-zA-Z0-9._-]+"
```

TOML is also supported (`mcp-test.toml`). The harness auto-discovers the config file in the current directory. CLI flags always override config file values.

Then just run:

```bash
mcp-test
```

---

## All five assertion types

**assert_tool_call** -- invoke a tool and validate the response:

```python
async def test_add_tool(mcp_server):
    await assert_tool_call(mcp_server, "add", {"a": 1, "b": 2})

    await assert_tool_call(
        mcp_server, "add", {"a": 1, "b": 2},
        expected=[{"text": "3", "isError": False}],
    )

    result = await assert_tool_call(mcp_server, "get_users", {})
    assert len(result.content) > 0
```

**assert_resource_read** -- read a resource and check content/MIME type:

```python
async def test_config_resource(mcp_server):
    await assert_resource_read(
        mcp_server, "file:///config.json",
        expected_content='{"debug": true}',
        expected_mime_type="application/json",
    )
```

**assert_prompt** -- get a prompt and validate message structure:

```python
async def test_summarize_prompt(mcp_server):
    await assert_prompt(
        mcp_server, "summarize",
        arguments={"text": "The quick brown fox."},
        expected_messages=[
            {"role": "assistant", "content": "Summary: A fox."},
        ],
    )
```

**assert_capabilities** -- verify server capabilities from the handshake:

```python
async def test_server_capabilities(mcp_server):
    await assert_capabilities(mcp_server, {
        "tools": {},
        "resources": {},
    })
```

**assert_snapshot** -- compare response against a stored snapshot:

```python
from pathlib import Path
from mcp_test_harness import assert_snapshot

async def test_report_output_stable(mcp_server):
    result = await mcp_server.call_tool("generate_report", {"format": "json"})
    await assert_snapshot(result, "report_json", test_file=Path(__file__))
```

All assertions produce diff-style output on failure showing expected vs actual values.

---

## Fixtures -- setup and teardown

Built-in fixtures:

| Fixture | Scope | Description |
|---------|-------|-------------|
| `mcp_server` | Per-test | Fresh ClientSession for each test |
| `mcp_server_session` | Per-module | Shared ClientSession across all tests in a file |

Custom fixtures:

```python
from mcp_test_harness.fixtures import fixture, FixtureScope

@fixture
async def api_key():
    return "test-key-12345"

@fixture
async def test_database():
    db = await connect_to_test_db()
    yield db
    await db.close()

@fixture(scope=FixtureScope.PER_MODULE)
async def shared_resource():
    resource = await create_expensive_resource()
    yield resource
    await resource.cleanup()

async def test_with_fixtures(mcp_server, test_database, api_key):
    result = await mcp_server.call_tool("query", {
        "db": test_database.url,
        "key": api_key,
    })
    assert result is not None
```

---

## Markers -- timeout, retry, skip, tags

```python
from mcp_test_harness import marker, skip

@marker(timeout=120)
async def test_slow_computation(mcp_server):
    await assert_tool_call(mcp_server, "train_model", {"epochs": 100})

@marker(retry=3)
async def test_external_api(mcp_server):
    await assert_tool_call(mcp_server, "fetch_weather", {"city": "NYC"})

@marker(tags=["smoke", "critical"])
async def test_health_check(mcp_server):
    await assert_capabilities(mcp_server, {"tools": {}})

@skip(reason="Waiting on server fix #42")
async def test_broken_feature(mcp_server):
    pass
```

Filter from CLI:

```bash
mcp-test -m smoke
mcp-test -k health
mcp-test -k "*workflow*"
```

---

## Snapshot testing

```python
from pathlib import Path
from mcp_test_harness import assert_snapshot

async def test_user_list_stable(mcp_server):
    result = await mcp_server.call_tool("list_users", {})
    await assert_snapshot(result, "user_list", test_file=Path(__file__))
```

First run creates the snapshot. Subsequent runs compare against it. Update after intentional changes:

```bash
mcp-test --update-snapshots
```

---

## Schema validation

By default, every JSON-RPC response is validated against the MCP specification:
- JSON-RPC 2.0 envelope structure
- Error objects have code (integer) and message (string)
- Tool input schemas are valid JSON Schema
- Resource URIs match declared URI templates

Disable if needed:

```yaml
schema_validation: false
```

---

## Reports for CI

```bash
# JUnit XML (GitHub Actions, Jenkins, GitLab CI)
mcp-test --report-format junit --report-output reports/results.xml

# JSON (custom dashboards, includes full metadata)
mcp-test --report-format json --report-output reports/results.json
```

---

## Parallel execution

```bash
mcp-test --parallel
mcp-test --parallel --workers 4
```

Each worker gets its own server instance. If one crashes, others continue.

---

## Testing remote servers (SSE and HTTP)

```bash
mcp-test --transport sse --server-command "http://localhost:8080/sse" tests/
mcp-test --transport http --server-command "http://localhost:8080/mcp" tests/
```

With auth headers:

```yaml
server:
  command: http://localhost:8080/sse
  transport: sse
  transport_options:
    headers:
      Authorization: "Bearer my-token"
```

---

## GitHub Action

```yaml
- name: Test MCP Server
  uses: ./.github/actions/mcp-test
  with:
    server-command: "python my_server.py"
    test-directory: "tests/"
    report-format: "junit"
```

| Input | Default | Description |
|-------|---------|-------------|
| `server-command` | `""` | Shell command to start the server |
| `transport` | `stdio` | Transport type |
| `test-directory` | `tests/` | Path to test files |
| `config-file` | `""` | Path to config file |
| `report-format` | `junit` | Report format |
| `harness-version` | `latest` | Version to install |

---

## Plugins

Extend the harness with custom assertions, fixtures, reporters, and transports:

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

Load via config or Python entry points. See `examples/reference_plugin.py`.

---

## Standalone binary

```bash
pip install -e ".[dev]"
python scripts/build_binary.py
dist/mcp-test --version
```

No Python required on the target machine.

---

## Dependency management (mcplint shim)

The `mcplint` sub-package pins MCP ecosystem dependencies. It provides version helpers:

```python
from mcplint import bastion_version, bedrock_version

print(bastion_version())    # e.g. "1.0.12"
print(bedrock_version())    # None if bedrock extra not installed
```

This is useful for CI checks and health endpoints. If you need security middleware for your MCP server (prompt injection defense, PII redaction, RBAC, rate limits), see [MCP-Bastion](https://github.com/vaquarkhan/MCP-Bastion) -- a separate project that MCPLint can optionally pull in as a dependency.

---

## CLI reference

```
mcp-test [TEST_PATH] [OPTIONS]

  --server-command CMD     Shell command to start the MCP server
  --transport TYPE         stdio | sse | http (default: stdio)
  --config PATH            Path to mcp-test.yaml or mcp-test.toml
  --timeout SECONDS        Per-test timeout (default: 30)
  --parallel               Run tests in parallel
  --workers N              Number of parallel workers (default: CPU count)
  -k PATTERN               Filter tests by name
  -m MARKER                Filter tests by marker or tag
  --report-format FORMAT   json | junit
  --report-output PATH     Path to write the report file
  --verbose                Full server communication logs
  --update-snapshots       Overwrite stored snapshots
  --version                Print version and exit
```

Exit codes: 0 = all passed, 1 = failures/errors, 2 = config error

---

## Configuration file reference

```yaml
server:
  command: python my_server.py
  transport: stdio
  transport_options: {}

test:
  dirs: [tests/]
  timeout: 30
  parallel: false
  workers: 4

report:
  format: junit
  output: reports/results.xml

schema_validation: true
plugins: []
redact_patterns: []
```

---

## Project layout

```
MCPLint/
+-- pyproject.toml
+-- mcp_test_harness.spec
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
|       +-- assertions.py           # assert_tool_call, etc.
|       +-- schema.py               # JSON-RPC / MCP schema validation
|       +-- fixtures.py             # fixture manager
|       +-- plugins.py              # plugin registry
|       +-- reporting.py            # console, JSON, JUnit reporters
|       +-- snapshots.py            # snapshot testing
|       +-- parser.py               # JSON-RPC message parser
|       +-- models.py               # shared data models
+-- examples/
+-- scripts/
+-- tests/                          # 370 unit tests, 96% coverage
+-- docs/
|   +-- DEVELOPER_GUIDE.md         # complete API and integration guide
|   +-- TUTORIAL.md                # step-by-step tutorial
|   +-- DECISIONS.md               # architecture decisions
+-- .github/
    +-- actions/mcp-test/           # reusable GitHub Action
    +-- workflows/validate.yml      # CI pipeline
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `mcp-test: command not found` | Run `pip install -e ".[dev]"` |
| Tests hang | Check `--timeout`; server may not respond to MCP handshake |
| `No tests discovered` | Files must match `test_*.py` or `*_test.py`; functions must start with `test_` |
| Snapshot mismatch after intentional change | Run `mcp-test --update-snapshots` |
| Server crashes during tests | Check server logs; harness marks remaining tests as errored |
| Config file not found | Harness looks for `mcp-test.yaml` / `mcp-test.toml` in cwd, or use `--config` |

---

## License

Non-commercial use only with mandatory attribution.

Author: Vaquar Khan -- https://github.com/vaquarkhan

See [LICENSE](LICENSE) for full terms. Contact the author for commercial licensing.
