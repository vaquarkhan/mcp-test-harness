# MCP Test Harness -- Step-by-Step Tutorial

Author: [Vaquar Khan](https://github.com/vaquarkhan)

This tutorial walks you through testing an MCP server from scratch. By the end you will have automated tests running in CI with JUnit reports.

---

## Prerequisites

- Python 3.10 or later
- An MCP server you want to test (we will create a simple one below)
- 10 minutes

---

## 1. Install MCP Test Harness

```bash
git clone https://github.com/vaquarkhan/mcp-test-harness.git
cd mcp-test-harness

python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install --upgrade pip
pip install -e ".[dev]"
```

Confirm the CLI is available:

```bash
mcp-test --version
# mcp-test 1.0.0
```

---

## 2. Create a sample MCP server to test

Create `my_server.py` in the project root. This is a minimal MCP server using the official Python SDK:

```python
"""Minimal MCP server for testing."""
import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server

app = Server("demo-server")

@app.tool()
async def echo(message: str) -> str:
    """Echo the input message back."""
    return message

@app.tool()
async def add(a: int, b: int) -> str:
    """Add two numbers."""
    return str(a + b)

async def main():
    async with stdio_server() as (read, write):
        await app.run(read, write, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 3. Write your first test file

Create `tests/test_demo_server.py`:

```python
"""Tests for the demo MCP server."""

from mcp_test_harness import assert_tool_call, assert_capabilities


async def test_server_has_tool_capabilities(mcp_server):
    """The server should advertise tool support during the MCP handshake."""
    await assert_capabilities(mcp_server, {"tools": {}})


async def test_echo_returns_input(mcp_server):
    """The echo tool should return exactly what we send."""
    await assert_tool_call(mcp_server, "echo", {"message": "hello"})


async def test_add_two_numbers(mcp_server):
    """The add tool should return the sum as a string."""
    await assert_tool_call(
        mcp_server,
        "add",
        {"a": 2, "b": 3},
        expected=[{"text": "5", "isError": False}],
    )
```

The `mcp_server` parameter is a built-in fixture. You do not need to create it -- the harness handles server startup, connection, and shutdown automatically.

---

## 4. Run the tests

```bash
mcp-test --server-command "python my_server.py" tests/test_demo_server.py
```

Expected output:

```
  [PASS] test_server_has_tool_capabilities (52.1ms)
  [PASS] test_echo_returns_input (34.7ms)
  [PASS] test_add_two_numbers (28.3ms)

3 passed, 0 failed, 0 errored, 0 skipped
Total time: 415.2ms
```

---

## 5. Create a config file so you don't repeat yourself

Create `mcp-test.yaml` in the project root:

```yaml
server:
  command: python my_server.py
  transport: stdio

test:
  dirs:
    - tests/
  timeout: 30
```

Now you can just run:

```bash
mcp-test
```

---

## 6. Add more assertion types

Create `tests/test_assertions_demo.py`:

```python
"""Demonstrate all five assertion types."""

from pathlib import Path
from mcp_test_harness import (
    assert_tool_call,
    assert_resource_read,
    assert_prompt,
    assert_capabilities,
    assert_snapshot,
)


async def test_tool_call_basic(mcp_server):
    """Call a tool and let the harness check for errors."""
    await assert_tool_call(mcp_server, "echo", {"message": "test"})


async def test_tool_call_with_expected(mcp_server):
    """Call a tool and validate the exact response."""
    await assert_tool_call(
        mcp_server, "add", {"a": 10, "b": 20},
        expected=[{"text": "30", "isError": False}],
    )


async def test_tool_call_return_value(mcp_server):
    """Use the return value for custom assertions."""
    result = await assert_tool_call(mcp_server, "echo", {"message": "hi"})
    assert len(result.content) == 1


# Uncomment these if your server supports resources and prompts:

# async def test_resource_read(mcp_server):
#     await assert_resource_read(
#         mcp_server, "file:///config.json",
#         expected_content='{"debug": true}',
#         expected_mime_type="application/json",
#     )

# async def test_prompt(mcp_server):
#     await assert_prompt(
#         mcp_server, "greeting",
#         arguments={"name": "Alice"},
#         expected_messages=[{"role": "assistant", "content": "Hello, Alice!"}],
#     )


async def test_capabilities(mcp_server):
    """Verify the server advertises expected capabilities."""
    await assert_capabilities(mcp_server, {"tools": {}})


async def test_snapshot(mcp_server):
    """Snapshot the echo response for regression detection."""
    result = await mcp_server.call_tool("echo", {"message": "snapshot test"})
    await assert_snapshot(result, "echo_snapshot", test_file=Path(__file__))
```

---

## 7. Use markers to control test behavior

Create `tests/test_markers_demo.py`:

```python
"""Demonstrate markers: timeout, retry, skip, tags."""

from mcp_test_harness import marker, skip, assert_tool_call


@marker(timeout=5)
async def test_with_short_timeout(mcp_server):
    """This test fails if it takes more than 5 seconds."""
    await assert_tool_call(mcp_server, "echo", {"message": "fast"})


@marker(retry=2)
async def test_with_retry(mcp_server):
    """If this fails, it retries up to 2 more times."""
    await assert_tool_call(mcp_server, "echo", {"message": "retry me"})


@marker(tags=["smoke"])
async def test_tagged_smoke(mcp_server):
    """Tagged as 'smoke' -- run with: mcp-test -m smoke"""
    await assert_tool_call(mcp_server, "echo", {"message": "smoke"})


@skip(reason="Not implemented yet")
async def test_future_feature(mcp_server):
    """This test is skipped and shows the reason in the report."""
    pass
```

Run only smoke tests:

```bash
mcp-test -m smoke
```

Run only tests matching a name pattern:

```bash
mcp-test -k "retry"
```

---

## 8. Create custom fixtures

Create `tests/test_fixtures_demo.py`:

```python
"""Demonstrate custom fixtures."""

from mcp_test_harness import assert_tool_call
from mcp_test_harness.fixtures import fixture, FixtureScope


@fixture
async def test_message():
    """Simple fixture that returns a test message."""
    return "hello from fixture"


@fixture
async def temp_data():
    """Fixture with setup and teardown."""
    data = {"created": True}
    yield data                  # test runs here
    data["created"] = False     # teardown


@fixture(scope=FixtureScope.PER_MODULE)
async def shared_config():
    """Shared across all tests in this file (created once)."""
    return {"server": "demo", "timeout": 30}


async def test_with_message_fixture(mcp_server, test_message):
    """The test_message fixture is injected by parameter name."""
    await assert_tool_call(mcp_server, "echo", {"message": test_message})


async def test_with_temp_data(mcp_server, temp_data):
    """temp_data is created before the test and cleaned up after."""
    assert temp_data["created"] is True


async def test_with_shared_config(mcp_server, shared_config):
    """shared_config is the same object for all tests in this file."""
    assert shared_config["server"] == "demo"
```

---

## 9. Generate CI reports

JUnit XML for GitHub Actions / Jenkins:

```bash
mcp-test --report-format junit --report-output reports/results.xml
```

JSON for custom dashboards:

```bash
mcp-test --report-format json --report-output reports/results.json
```

Add to your config file:

```yaml
report:
  format: junit
  output: reports/results.xml
```

---

## 10. Run tests in parallel

```bash
mcp-test --parallel --workers 4
```

Each worker starts its own server instance. Results are merged into one report.

---

## 11. Test a remote server

For servers running over SSE or HTTP:

```bash
# SSE
mcp-test --transport sse --server-command "http://localhost:8080/sse" tests/

# Streamable HTTP
mcp-test --transport http --server-command "http://localhost:8080/mcp" tests/
```

---

## 12. Add to GitHub Actions

Create `.github/workflows/mcp-tests.yml`:

```yaml
name: MCP Server Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Test MCP Server
        uses: ./.github/actions/mcp-test
        with:
          server-command: "python my_server.py"
          test-directory: "tests/"
          report-format: "junit"
```

---

## 13. Update snapshots after intentional changes

When your server's output changes intentionally:

```bash
mcp-test --update-snapshots
```

This overwrites all stored snapshots with current responses. Review the diff in git before committing.

---

## 14. Write and load a plugin

Create `my_plugin.py`:

```python
from mcp_test_harness.plugins import PluginContext

class TimingPlugin:
    name = "timing"

    def register(self, context: PluginContext):
        context.add_assertion("assert_fast", self.assert_fast)

    async def assert_fast(self, session, tool_name, max_ms=100):
        import time
        start = time.monotonic()
        result = await session.call_tool(tool_name, {})
        elapsed = (time.monotonic() - start) * 1000
        assert elapsed < max_ms, f"Too slow: {elapsed:.0f}ms"
        return result

plugin = TimingPlugin()
```

Add to config:

```yaml
plugins:
  - my_plugin.py
```

---

## Summary

You now know how to:
- Write async test functions with built-in fixtures
- Use all five assertion types
- Control tests with markers (timeout, retry, skip, tags)
- Capture snapshots for regression detection
- Generate JUnit/JSON reports for CI
- Run tests in parallel
- Test remote servers over SSE/HTTP
- Extend the harness with plugins
- Integrate with GitHub Actions

For the full CLI reference and config file options, see the [README](../README.md).

---

## License

Non-commercial use with mandatory attribution.
See [LICENSE](../LICENSE) for full terms. You may use [CITATION.cff](../CITATION.cff) to cite the project in papers or public write-ups (optional).

Attribution: Vaquar Khan -- https://github.com/vaquarkhan
