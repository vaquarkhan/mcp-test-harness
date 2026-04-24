# MCP Test Harness Developer Guide

Author: Vaquar Khan -- https://github.com/vaquarkhan

**Before this deep-dive:** the documentation **hub** and **adoption paths** (same style as [MCP-Bastion](https://github.com/vaquarkhan/MCP-Bastion)) live in [README.md in this `docs/` folder](README.md). For a short path to first green run, see [QUICK_START.md](QUICK_START.md). For **CI, JUnit, and whether to publish report files**, see [CI_AND_REPORTS.md](CI_AND_REPORTS.md). For **runnable and copy-paste examples** (assertion demo, config validation, `mcp-test.yaml` sample), see [../examples/README.md](../examples/README.md). For **harness repo** layout and running the full `pytest` suite, see [DEVELOPER.md](DEVELOPER.md).

This guide explains how to add automated MCP server testing to your project
using MCP Test Harness. It covers everything from initial setup to advanced patterns.

---

## Who this guide is for

You have an MCP server (written in Python, TypeScript, Go, or any language)
and you want automated tests that:

- Run on every commit in CI
- Validate tool calls, resource reads, and prompt responses
- Catch protocol violations and regressions
- Produce JUnit/JSON reports for your pipeline

---

## Part 1: Adding MCP Test Harness to your project

### Option A: Install from pip (when published)

```bash
pip install mcplint
```

### Option B: Install from source (current)

```bash
# Add to your requirements.txt or pyproject.toml
# For now, clone and install in editable mode:
git clone https://github.com/vaquarkhan/mcp-test-harness.git
pip install -e "./mcp-test-harness[dev]"
```

### Option C: Add as a dependency in your pyproject.toml

```toml
[project.optional-dependencies]
test = [
    "mcplint>=0.1.0",
]
```

### Verify installation

```bash
mcp-test --version
# mcp-test 1.0.0
```

### Scaffold starter files (optional)

From your project root (where you want `tests/` and `mcp-test.yaml`):

```bash
mcp-test init
mcp-test init --server-command "python -m your_package.mcp"   # set command in one step
mcp-test init --help
```

This creates a ready-to-edit test module using the `mcp_server` fixture and comments showing `assert_tool_call` / `assert_tool_list`. Editor users can copy snippets from `.vscode/mcp-test-harness.code-snippets` in the harness repository (prefixes like `mcp-assert-tool`).

---

## Part 2: Project structure

After setup, your project should look like this:

```
your-mcp-server/
+-- your_server.py              # your MCP server code
+-- mcp-test.yaml               # MCP Test Harness configuration
+-- tests/
|   +-- test_tools.py           # tool call tests
|   +-- test_resources.py       # resource read tests
|   +-- test_capabilities.py    # capability tests
|   +-- __snapshots__/          # auto-generated snapshot files
+-- .github/
    +-- workflows/
        +-- test.yml            # CI workflow
```

---

## Part 3: Configuration

### Minimal configuration (mcp-test.yaml)

```yaml
server:
  command: python your_server.py
```

That is all you need to start. The harness uses sensible defaults:
- Transport: stdio
- Timeout: 30 seconds per test
- Test directory: tests/
- Schema validation: enabled

### Full configuration reference

```yaml
# mcp-test.yaml

server:
  # REQUIRED: command to start your MCP server
  command: python your_server.py

  # Transport protocol (default: stdio)
  # Options: stdio, sse, http
  transport: stdio

  # Extra transport options (for SSE/HTTP servers)
  transport_options:
    host: localhost
    port: 8080
    path: /mcp
    headers:
      Authorization: "Bearer your-token"

test:
  # Directories to search for test files (default: [tests/])
  dirs:
    - tests/
    - integration_tests/

  # Per-test timeout in seconds (default: 30)
  timeout: 30

  # Run tests in parallel (default: false)
  parallel: false

  # Number of parallel workers (default: CPU count)
  workers: 4

report:
  # Output format: json or junit (default: none)
  format: junit

  # File path for the report (default: none)
  output: reports/results.xml

# Validate all JSON-RPC responses against MCP spec (default: true)
schema_validation: true

# Plugin file paths or module names to load (default: [])
plugins:
  - my_custom_plugin.py

# Regex patterns to redact from verbose output (default: [])
# Useful for hiding API keys and tokens in logs
redact_patterns:
  - "sk-[a-zA-Z0-9]+"
  - "Bearer [a-zA-Z0-9._-]+"
```

### TOML format (alternative)

```toml
# mcp-test.toml

[server]
command = "python your_server.py"
transport = "stdio"

[test]
dirs = ["tests/"]
timeout = 30

[report]
format = "junit"
output = "reports/results.xml"

schema_validation = true
plugins = []
```

### Config file discovery

The harness looks for config files in this order:
1. Path specified by `--config` flag
2. `mcp-test.yaml` in the current directory
3. `mcp-test.yml` in the current directory
4. `mcp-test.toml` in the current directory

CLI flags always override config file values.

### `mcp-test` CLI flags (reference)

| Flag | Description |
|------|-------------|
| `--server-command` | Command to start the MCP server (or URL for SSE/HTTP) |
| `--transport` | `stdio` (default), `sse`, or `http` |
| `--config` | Path to `mcp-test.yaml` / `mcp-test.toml` |
| `--timeout` | Default per-test timeout (seconds) |
| `--parallel` | Run tests in parallel (multiple workers) |
| `--workers` | Number of workers when `--parallel` is set |
| `--report-format` / `--report-output` | `json`, `junit`, or `html` report to a file |
| `--update-snapshots` | Overwrite snapshot files |
| `-k` / `-m` | Filter tests by name or marker/tag |
| `--list` | List discovered tests and exit |
| `--watch` | Re-run the suite when any `*.py` under the test paths changes (1s poll). Not compatible with `--list`. |
| `--verbose` | Verbose logging |

---

## Part 3b: Reliability features (v0.1+)

### Post-connect protocol validation (`schema_validation: true`)

When enabled (the default), after a successful `initialize` handshake the harness:

- Validates the `initialize` result shape (protocol version, capabilities, `serverInfo`).
- Calls `tools/list` and checks each tool’s `name` and `inputSchema`, and validates `inputSchema` as a JSON Schema (when the `jsonschema` package is installed).
- Optionally calls `resources/list` and `prompts/list` when the server supports them, and checks basic field shapes.

If anything fails, startup aborts with `StartupError` and a message listing the first violations. This runs for both sequential and parallel schedulers. Set `schema_validation: false` in config to skip (for debugging only).

### Stdio process monitoring

For `transport: stdio`, the client keeps a handle to the server subprocess. If the process exits while tests are still running, the harness raises `ServerCrashedError` instead of waiting for a generic timeout. Remote transports (SSE/HTTP) have no local process, so this does not apply.

### Parallel execution and per-module fixtures

Workers are given **entire test modules** (all tests from the same `test_*.py` file) in round-robin order, not isolated single tests. That way **`mcp_server_session`** and other per-module fixtures stay on one worker and remain meaningful. Use sequential mode if you need global ordering across files.

### Command parsing (`stdio`)

The server command string is split with Python’s `shlex.split` (not plain `str.split`), so quoted arguments and spaces are handled like a shell. Example: `python -c "print(1)"` is parsed as one executable plus correct argv.

### Test discovery and broken files

If a `test_*.py` file cannot be imported (syntax error, `ImportError`, etc.), the harness logs a **warning** with the file path and traceback, then skips that file. Check logs when you see “0 tests discovered” unexpectedly.

### Fixture dependency cycles

If fixture `A` depends on `B` and `B` depends on `A` (or any cycle), resolution raises `FixtureError: Circular fixture dependency` instead of a `RecursionError`.

### Additional assertions (API)

| Function | Use |
|----------|-----|
| `assert_tool_call(..., validate_against_input_schema=True)` | Validate arguments with `jsonschema` before calling the tool (requires `jsonschema`). |
| `assert_tool_schema(session, name, expected_input_schema)` | Assert a tool’s `inputSchema` dict exactly. |
| `assert_protocol_version(session, expected="2024-11-05")` | Compare negotiated protocol version (requires a harness-started session, which sets `_mcp_harness_init_result`). |
| `assert_tool_idempotent(...)` | Same tool+args `n` times; identical results. |
| `assert_latency(..., max_ms=..., runs=..., aggregate=...)` | Latency budget on a tool call; optional multi-run p95/p99 and warmup (see [PERFORMANCE.md](PERFORMANCE.md)). |
| `assert_tool_call_validates_input(...)` | Assert the server rejects bad arguments; wraps `assert_tool_rejects`. |
| `assert_snapshot(..., ignore_fields=[...], mask_patterns=[...])` | Snapshots: drop volatile keys or mask strings matching regexes. |

---

## Part 4: Writing tests

### Test file naming

The harness discovers test files matching these patterns:
- `test_*.py` (prefix)
- `*_test.py` (suffix)

Test functions must start with `test_` and can be sync or async:

```python
# tests/test_my_server.py

# Async test (recommended -- MCP protocol is async)
async def test_echo(mcp_server):
    ...

# Sync test (also works)
def test_simple_check():
    assert 1 + 1 == 2
```

Test classes must start with `Test`:

```python
class TestEchoTool:
    async def test_basic(self, mcp_server):
        ...

    async def test_empty_input(self, mcp_server):
        ...
```

### The mcp_server fixture

Every test that needs to talk to your MCP server should declare
`mcp_server` as a parameter. The harness:

1. Starts your server using the configured command
2. Connects via the configured transport (stdio/SSE/HTTP)
3. Performs the MCP initialize handshake
4. Passes the connected ClientSession to your test
5. Shuts down the server after the test

```python
async def test_my_tool(mcp_server):
    # mcp_server is a connected MCP ClientSession
    # You can call tools, read resources, get prompts
    result = await mcp_server.call_tool("my_tool", {"arg": "value"})
```

### mcp_server vs mcp_server_session

| Fixture | Scope | Server lifecycle | Use when |
|---------|-------|-----------------|----------|
| `mcp_server` | Per-test | New server for each test | Tests modify server state |
| `mcp_server_session` | Per-module | Shared server for all tests in file | Read-only tests, faster |

```python
# Each test gets its own server (safe for state-changing tests)
async def test_create_item(mcp_server):
    await mcp_server.call_tool("create", {"name": "test"})

# All tests in this file share one server (faster)
async def test_list_items(mcp_server_session):
    await mcp_server_session.call_tool("list", {})

async def test_count_items(mcp_server_session):
    await mcp_server_session.call_tool("count", {})
```

---

## Part 5: Assertion reference

### assert_tool_call

Invokes a tool on the server and validates the response.

```python
from mcp_test_harness import assert_tool_call

# Basic: call the tool, fail if server returns an error
await assert_tool_call(mcp_server, "echo", {"message": "hello"})

# With expected output: fail if response doesn't match
await assert_tool_call(
    mcp_server,
    "add",
    {"a": 1, "b": 2},
    expected=[{"text": "3", "isError": False}],
)

# Use the return value for custom checks
result = await assert_tool_call(mcp_server, "get_data", {})
assert len(result.content) > 0
assert result.content[0].text == "expected value"
```

Parameters:
- `session` -- the MCP ClientSession (usually `mcp_server`)
- `tool_name` -- name of the tool to call
- `arguments` -- dict of arguments to pass to the tool
- `expected` (optional) -- expected response content to compare against

Fails when:
- The tool returns an error response (isError: true)
- The response doesn't match `expected` (shows a diff)

### assert_resource_read

Reads a resource from the server and validates content and MIME type.

```python
from mcp_test_harness import assert_resource_read

# Check content only
await assert_resource_read(
    mcp_server,
    "file:///config.json",
    expected_content='{"debug": true}',
)

# Check MIME type only
await assert_resource_read(
    mcp_server,
    "file:///data.csv",
    expected_mime_type="text/csv",
)

# Check both
await assert_resource_read(
    mcp_server,
    "file:///readme.md",
    expected_content="# Hello",
    expected_mime_type="text/markdown",
)
```

Parameters:
- `session` -- the MCP ClientSession
- `resource_uri` -- URI of the resource to read
- `expected_content` (optional) -- expected text content
- `expected_mime_type` (optional) -- expected MIME type string

Fails when:
- The resource returns no content
- Content doesn't match `expected_content`
- MIME type doesn't match `expected_mime_type`

### assert_prompt

Gets a prompt from the server and validates the message structure.

```python
from mcp_test_harness import assert_prompt

await assert_prompt(
    mcp_server,
    "summarize",
    arguments={"text": "Long text here..."},
    expected_messages=[
        {"role": "assistant", "content": "Summary: ..."},
    ],
)

# Without expected messages (just verify the prompt exists)
result = await assert_prompt(mcp_server, "greeting")
assert len(result.messages) > 0
```

Parameters:
- `session` -- the MCP ClientSession
- `prompt_name` -- name of the prompt
- `arguments` (optional) -- dict of arguments for the prompt
- `expected_messages` (optional) -- list of expected message dicts

Fails when:
- Messages don't match `expected_messages` (shows a diff)

### assert_capabilities

Verifies the server advertises expected capabilities from the MCP handshake.

```python
from mcp_test_harness import assert_capabilities

# Check that the server supports tools
await assert_capabilities(mcp_server, {"tools": {}})

# Check multiple capabilities
await assert_capabilities(mcp_server, {
    "tools": {},
    "resources": {},
    "prompts": {},
})
```

This is a subset check -- extra capabilities on the server are fine.
Only the keys you specify are checked.

Parameters:
- `session` -- the MCP ClientSession
- `expected` -- dict of expected capabilities

Fails when:
- A specified capability is missing from the server
- A capability value doesn't match

### assert_snapshot

Compares a value against a stored snapshot file for regression detection.

```python
from pathlib import Path
from mcp_test_harness import assert_snapshot

async def test_output_stable(mcp_server):
    result = await mcp_server.call_tool("generate", {})
    await assert_snapshot(
        result,                    # value to snapshot
        "generate_output",         # snapshot name (becomes filename)
        test_file=Path(__file__),  # determines snapshot directory
    )
```

Parameters:
- `actual` -- the value to compare (JSON-serialized)
- `snapshot_name` -- logical name (used as `__snapshots__/<name>.snap`)
- `test_file` -- path to the test file (snapshots stored adjacent)
- `update` (optional) -- if True, overwrite the snapshot

Behavior:
- First run: creates the snapshot file, test passes
- Later runs: compares against stored snapshot
- Mismatch: fails with a unified diff
- Update: `mcp-test --update-snapshots` overwrites all snapshots

Snapshot files are JSON and should be committed to version control.

---

## Part 6: Fixture reference

### Built-in fixtures

| Name | Scope | Description |
|------|-------|-------------|
| `mcp_server` | Per-test | Fresh MCP ClientSession, new server per test |
| `mcp_server_session` | Per-module | Shared MCP ClientSession, one server per file |

### Custom fixtures

Use the `@fixture` decorator to create your own:

```python
from mcp_test_harness.fixtures import fixture, FixtureScope

# Simple fixture (per-test scope, no teardown)
@fixture
async def api_key():
    return "test-key-12345"

# Fixture with setup and teardown
@fixture
async def database():
    db = await connect()       # setup
    yield db                   # test runs here
    await db.disconnect()      # teardown

# Per-module scope (shared across tests in one file)
@fixture(scope=FixtureScope.PER_MODULE)
async def shared_client():
    client = await create_client()
    yield client
    await client.close()

# Sync fixture (also works)
@fixture
def config():
    return {"timeout": 30, "retries": 3}
```

### How fixture injection works

The harness inspects your test function's parameter names and matches
them to registered fixtures:

```python
# The harness sees parameters: mcp_server, database, api_key
# It resolves each by name from the fixture registry
async def test_query(mcp_server, database, api_key):
    result = await mcp_server.call_tool("query", {
        "db_url": database.url,
        "key": api_key,
    })
```

### Fixture scoping rules

- `PER_TEST` (default): created before each test, torn down after
- `PER_MODULE`: created once per test file, torn down after all tests in that file

Teardown errors are logged but do not change the test's pass/fail status.

### Fixture dependencies

Fixtures can depend on other fixtures:

```python
@fixture
async def auth_token():
    return "token-123"

@fixture
async def authenticated_client(auth_token):
    # auth_token is injected automatically
    return Client(token=auth_token)

async def test_with_client(mcp_server, authenticated_client):
    ...
```

---

## Part 7: Marker reference

### @marker decorator

```python
from mcp_test_harness import marker

@marker(timeout=60)           # custom timeout (seconds)
@marker(retry=3)              # retry up to 3 times on failure
@marker(tags=["smoke"])       # tag for filtering
@marker(timeout=60, retry=2, tags=["slow", "integration"])  # combine
```

### @skip decorator

```python
from mcp_test_harness import skip

@skip                              # skip unconditionally
@skip(reason="Bug #42")           # skip with reason (shown in report)
```

### Marker parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `timeout` | float | Per-test timeout in seconds (overrides default) |
| `retry` | int | Number of retry attempts on failure |
| `tags` | list[str] | Tags for filtering with `-m` |
| `skip` | bool | Skip this test |
| `reason` | str | Reason for skipping (shown in report) |

### Filtering from CLI

```bash
# By tag
mcp-test -m smoke
mcp-test -m integration

# By name (substring match)
mcp-test -k echo
mcp-test -k "test_add"

# By name (glob pattern)
mcp-test -k "*workflow*"
mcp-test -k "test_?cho"
```

### Flaky test detection

When a test fails then passes on retry, it is marked as "flaky" in the
report. The test result is PASSED but with a flaky warning:

```
  [PASS] test_external_api (250.3ms)
      flaky (passed on retry)
```

The JSON report includes full retry history:

```json
{
  "name": "test_external_api",
  "status": "passed",
  "flaky": true,
  "retry_count": 2,
  "attempt_results": [
    {"attempt": 1, "status": "failed", "error": "timeout"},
    {"attempt": 2, "status": "failed", "error": "timeout"},
    {"attempt": 3, "status": "passed"}
  ]
}
```

---

## Part 8: Schema validation

The harness validates every JSON-RPC response from your server by default.

### What gets validated

| Check | Description |
|-------|-------------|
| JSON-RPC envelope | `jsonrpc` field is "2.0", `id` is string/int/null |
| Result/error exclusivity | Response has `result` or `error`, not both |
| Error object structure | `code` is integer, `message` is string |
| Tool input schemas | Advertised tool schemas are valid JSON Schema |
| Resource URI templates | Resource URIs match declared URI template patterns |

### Violations in reports

Schema violations appear in the JSON report:

```json
{
  "schema_violations": [
    {
      "json_path": "$.error.code",
      "expected_type": "integer",
      "actual_value": "NaN",
      "message": "'error.code' must be integer; got str"
    }
  ]
}
```

### Disabling validation

```yaml
# mcp-test.yaml
schema_validation: false
```

Or per-run:

```bash
# No CLI flag for this -- use config file
```

---

## Part 9: Reports

### Console output (always shown)

```
  [PASS] test_echo (45.2ms)
  [PASS] test_add (32.1ms)
  [FAIL] test_divide (18.5ms)
      Division by zero
      --- expected
      +++ actual
      @@ -1 +1 @@
      -"result": "inf"
      +"error": "division by zero"
  [SKIP] test_future (0.0ms)

3 passed, 1 failed, 0 errored, 1 skipped
Total time: 312.5ms
```

### JUnit XML

```bash
mcp-test --report-format junit --report-output results.xml
```

Compatible with GitHub Actions, Jenkins, GitLab CI, Azure DevOps.

### JSON

```bash
mcp-test --report-format json --report-output results.json
```

Includes:
- Harness version and MCP protocol version
- Server capabilities from the handshake
- Per-test: name, status, duration, error, traceback, assertion diff
- Retry history for flaky tests
- Schema violations

---

## Part 10: Running in CI

### GitHub Actions (using the built-in action)

```yaml
name: MCP Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Test MCP Server
        uses: ./.github/actions/mcp-test
        with:
          server-command: "python your_server.py"
          test-directory: "tests/"
          report-format: "junit"
```

### GitHub Actions (manual setup)

```yaml
name: MCP Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install
        run: pip install mcplint

      - name: Run tests
        run: |
          mcp-test \
            --server-command "python your_server.py" \
            --report-format junit \
            --report-output results.xml \
            tests/

      - name: Upload results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: test-results
          path: results.xml
```

### GitLab CI

```yaml
mcp-test:
  image: python:3.12
  script:
    - pip install mcplint
    - mcp-test --server-command "python your_server.py" --report-format junit --report-output results.xml tests/
  artifacts:
    reports:
      junit: results.xml
```

### Jenkins (Jenkinsfile)

```groovy
pipeline {
    agent { docker { image 'python:3.12' } }
    stages {
        stage('Test MCP Server') {
            steps {
                sh 'pip install mcplint'
                sh 'mcp-test --server-command "python your_server.py" --report-format junit --report-output results.xml tests/'
            }
            post {
                always {
                    junit 'results.xml'
                }
            }
        }
    }
}
```

---

## Part 11: Testing different server types

### Stdio server (local process)

Most common. The harness starts your server as a subprocess and
communicates via stdin/stdout.

```yaml
server:
  command: python your_server.py
  transport: stdio
```

Works with servers written in any language:

```yaml
# Node.js server
server:
  command: node your_server.js

# Go server
server:
  command: ./your_server

# Python with arguments
server:
  command: python -m your_package.server --port 0
```

### SSE server (remote, Server-Sent Events)

For servers already running and exposing an SSE endpoint:

```yaml
server:
  command: http://localhost:8080/sse
  transport: sse
```

### HTTP server (remote, streamable HTTP)

For servers using the MCP streamable HTTP transport:

```yaml
server:
  command: http://localhost:8080/mcp
  transport: http
```

### With authentication

```yaml
server:
  command: http://your-server.example.com/mcp
  transport: http
  transport_options:
    headers:
      Authorization: "Bearer ${MCP_TOKEN}"
```

---

## Part 12: Parallel execution

### When to use parallel mode

- Large test suites (50+ tests)
- Tests that are independent (no shared state)
- CI pipelines where speed matters

### How it works

Each parallel worker:
1. Starts its own server instance
2. Gets a subset of tests to run
3. Runs them independently
4. Reports results back

Results are merged into a single report.

### Configuration

```yaml
test:
  parallel: true
  workers: 4    # or omit for CPU count
```

Or from CLI:

```bash
mcp-test --parallel --workers 4
```

### What happens on server crash

If one worker's server crashes:
- That worker's remaining tests are marked as errored
- Other workers continue normally
- The final report includes all results

---

## Part 13: Plugins

### Plugin structure

A plugin is a Python module or class with a `name` attribute and a
`register(context)` method:

```python
from mcp_test_harness.plugins import PluginContext

class MyPlugin:
    name = "my-plugin"

    def register(self, context: PluginContext) -> None:
        # Register extensions here
        pass

plugin = MyPlugin()  # module-level instance for entry-point discovery
```

### What plugins can register

| Method | What it adds |
|--------|-------------|
| `context.add_assertion(name, func)` | Custom assertion function |
| `context.add_fixture(name, factory, scope)` | Custom fixture |
| `context.add_reporter(name, reporter)` | Custom report format |
| `context.add_transport(name, factory)` | Custom transport adapter |
| `context.add_discovery_hook(hook)` | Hook into test discovery |

### Loading plugins

Via config file:

```yaml
plugins:
  - path/to/my_plugin.py
  - my_package.plugin_module
```

Via Python entry points (auto-discovered on install):

```toml
# In your plugin package's pyproject.toml
[project.entry-points.mcp_test_harness]
my-plugin = "my_package.plugin:plugin"
```

### Example: latency assertion plugin

```python
import time
from mcp_test_harness.assertions import MCPAssertionError
from mcp_test_harness.plugins import PluginContext

class LatencyPlugin:
    name = "latency"

    def register(self, context: PluginContext) -> None:
        context.add_assertion("assert_response_time", assert_response_time)

async def assert_response_time(session, tool_name, arguments, max_ms=500):
    start = time.monotonic()
    result = await session.call_tool(tool_name, arguments)
    elapsed_ms = (time.monotonic() - start) * 1000
    if elapsed_ms > max_ms:
        raise MCPAssertionError(
            f"Tool '{tool_name}' took {elapsed_ms:.0f}ms (limit: {max_ms}ms)"
        )
    return result

plugin = LatencyPlugin()
```

See `examples/reference_plugin.py` for a complete example with a custom
assertion, fixture, and reporter.

---

## Part 14: Debugging test failures

### Verbose mode

```bash
mcp-test --verbose
```

Shows full JSON-RPC message exchange between the harness and your server.
Sensitive values matching `redact_patterns` are replaced with [REDACTED].

### Common failure patterns

**"No tests discovered"**
- Check file names match `test_*.py` or `*_test.py`
- Check function names start with `test_`
- Check the test directory path in config or CLI

**"MCP initialize handshake timed out"**
- Your server is not responding to the MCP protocol
- Check the server starts correctly: `python your_server.py`
- Check the transport type matches your server
- Increase timeout: `--timeout 60`

**"Server process exited unexpectedly"**
- Your server crashed during the test
- Check server logs for errors
- Run the server manually and test with the MCP Inspector first

**"Tool 'X' returned an error"**
- The tool raised an error on the server side
- The error message from the server is included in the test output
- Fix the tool implementation

**"Response mismatch" with diff**
- The tool returned a different response than expected
- Review the diff to see what changed
- Update the `expected` value or fix the server

**"Schema violation"**
- Your server's JSON-RPC response doesn't conform to the MCP spec
- Check the violation details (JSON path, expected type, actual value)
- Fix the response format in your server

**"Fixture error: No fixture registered for parameter 'X'"**
- Your test function has a parameter that doesn't match any fixture
- Check the parameter name matches a built-in or custom fixture
- Built-in fixtures: `mcp_server`, `mcp_server_session`

---

## Part 15: Best practices

### Test organization

```
tests/
+-- test_tools.py           # one file per tool or tool group
+-- test_resources.py       # resource read tests
+-- test_prompts.py         # prompt tests
+-- test_capabilities.py    # server capability tests
+-- test_error_handling.py  # edge cases and error responses
+-- test_regression.py      # snapshot tests for regression detection
```

### Use mcp_server_session for read-only tests

```python
# Faster: shared server for tests that don't modify state
async def test_list_tools(mcp_server_session):
    await assert_capabilities(mcp_server_session, {"tools": {}})

async def test_read_config(mcp_server_session):
    await assert_resource_read(mcp_server_session, "file:///config.json")
```

### Use mcp_server for state-changing tests

```python
# Safer: fresh server for tests that create/modify/delete
async def test_create_and_delete(mcp_server):
    await assert_tool_call(mcp_server, "create", {"name": "test"})
    await assert_tool_call(mcp_server, "delete", {"name": "test"})
```

### Tag tests for selective execution

```python
@marker(tags=["smoke"])
async def test_health(mcp_server):
    await assert_capabilities(mcp_server, {"tools": {}})

@marker(tags=["integration", "slow"])
async def test_full_workflow(mcp_server):
    ...
```

```bash
# Quick smoke tests on every PR
mcp-test -m smoke

# Full integration tests on main branch
mcp-test -m integration
```

### Use snapshots for complex responses

Instead of writing detailed expected values, snapshot the response:

```python
async def test_complex_output(mcp_server):
    result = await mcp_server.call_tool("generate_report", {"format": "json"})
    await assert_snapshot(result, "report_output", test_file=Path(__file__))
```

Review snapshot diffs in pull requests to catch unintended changes.

### Set appropriate timeouts

```python
# Fast tools: use default (30s) or shorter
@marker(timeout=5)
async def test_echo(mcp_server):
    ...

# Slow tools: increase timeout
@marker(timeout=120)
async def test_ml_inference(mcp_server):
    ...
```

### Use retry for known-flaky external dependencies

```python
@marker(retry=3, tags=["flaky"])
async def test_external_api(mcp_server):
    await assert_tool_call(mcp_server, "fetch_weather", {"city": "NYC"})
```

---

## Part 16: CLI quick reference

```
mcp-test [TEST_PATH] [OPTIONS]

  --server-command CMD     Command to start the MCP server
  --transport TYPE         stdio | sse | http (default: stdio)
  --config PATH            Path to config file
  --timeout SECONDS        Per-test timeout (default: 30)
  --parallel               Run tests in parallel
  --workers N              Parallel worker count (default: CPU count)
  -k PATTERN               Filter by test name
  -m MARKER                Filter by marker/tag
  --report-format FORMAT   json | junit
  --report-output PATH     Report file path
  --verbose                Show full server communication
  --update-snapshots       Overwrite stored snapshots
  --version                Print version
```

Exit codes:
- 0: all tests passed
- 1: one or more tests failed or errored
- 2: configuration error

---

## License

Non-commercial use with mandatory attribution.
See [LICENSE](../LICENSE) for full terms. [CITATION.cff](../CITATION.cff) lists how to cite the software in publications (optional).

Attribution: Vaquar Khan -- https://github.com/vaquarkhan
