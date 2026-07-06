# MCP trace capture (per-test JSON-RPC timeline)

> [!TIP]
> **Feature highlight (v1.3):** every test run records MCP method calls automatically. No extra imports in your tests — enable traces by choosing **HTML** or **JSON** report output.

When a test executes, the harness wraps the MCP session with a **trace recorder**. Each `initialize`, `list_tools`, `call_tool`, and related call becomes an ordered event with timestamps, payload summaries, and byte sizes.

## What you get

| Output | Field / UI |
|--------|------------|
| **JSON report** | `tests[].mcp_trace` — `events`, `event_count`, `stdio_pollution` |
| **HTML report** | Expandable **MCP trace timeline** per test (click to inspect request/response pairs) |
| **Console** | Unchanged — traces are in machine-readable artifacts |

`stdio_pollution` flags errors that look like **non-JSON noise on stdout** (a common MCP server bug when `print()` leaks into the stdio transport).

## Run with traces

```bash
mcp-test tests/ \
  --server-command "python -m your_server" \
  --report-format html \
  --report-output reports/mcp-test.html
```

Or in `mcp-test.yaml`:

```yaml
server:
  command: python -m your_server

report:
  format: html
  output: reports/mcp-test.html
```

Open the HTML file and expand a test row — the timeline shows each MCP round-trip in order.

## Example test (no trace-specific code)

```python
# tests/test_echo.py
from mcp_test_harness import marker
from mcp_test_harness.assertions import assert_tool_call

@marker(tags=["smoke"])
async def test_echo(mcp_server):
    await assert_tool_call(mcp_server, "echo", {"text": "hello"})
```

The trace is attached **after** the test completes and appears in the report under that test's name.

## JSON snippet (inspect in CI)

```json
{
  "name": "test_echo",
  "status": "passed",
  "mcp_trace": {
    "event_count": 4,
    "events": [
      {"t_ms": 12.5, "direction": "request", "method": "call_tool", "payload": {"args": ["echo", {"text": "hello"}], "kwargs": {}}, "bytes": 42},
      {"t_ms": 45.2, "direction": "response", "method": "call_tool", "payload": "...", "bytes": 128}
    ],
    "stdio_pollution": []
  }
}
```

## When to use traces

1. **Debugging flaky tests** — see exact call order and latency between MCP methods.
2. **CI artifacts** — upload HTML/JSON from Actions; reviewers inspect timelines without re-running locally.
3. **Stdio hygiene** — `stdio_pollution` hints catch servers that log to stdout instead of stderr.

## Runnable demo pack

See **[feature-demo/platform-qa/](feature-demo/platform-qa/README.md)** — includes tests that produce rich traces and a sample HTML config.

**Related:** [example_enhanced_reports.md](example_enhanced_reports.md) · [example_report_formats.md](example_report_formats.md)
