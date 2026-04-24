# Copy-paste patterns for your MCP test project

Use these fragments in **your** repository (a directory named `tests/` is discovered by default). This file lives under `examples/` in the harness repo and is **not** executed as a test.

For a **Postman / Newman** mental model (collections, environments, multi-step chains) and the **roadmap** for a possible declarative collection format, read [../docs/COLLECTIONS.md](../docs/COLLECTIONS.md).

---

## 1) Minimal `mcp-test.yaml` (stdio)

```yaml
server:
  command: python -m your_package.mcp_server

test:
  timeout: 60

report:
  format: junit
  output: reports/mcp-junit.xml
```

Run from the same directory: `mcp-test`

---

## 2) Test module with the built-in `mcp_server` fixture

The harness injects a live `ClientSession` when you list `mcp_server` as a parameter. Async tests only.

```python
# tests/test_smoke.py
from mcp_test_harness import marker
from mcp_test_harness.assertions import assert_tool_list

@marker(tags=["smoke"])
async def test_at_least_one_tool(mcp_server):
    await assert_tool_list(mcp_server, expected_tools=["echo"])
```

Run smoke tests only: `mcp-test -m smoke`

---

## 3) Markers, skip, and performance runs

```python
# tests/test_api.py
from mcp_test_harness import marker, skip
from mcp_test_harness.assertions import assert_tool_call, assert_latency

@marker(tags=["smoke"], order=1)
async def test_echo_happy(mcp_server):
    await assert_tool_call(mcp_server, "echo", {"text": "hi"})

@skip(reason="Enable when the staging server is available")
async def test_planned(mcp_server):
    ...

@marker(tags=["perf"])
async def test_echo_latency(mcp_server):
    await assert_latency(
        mcp_server,
        "echo",
        {"text": "x"},
        max_ms=2000.0,
        runs=5,
        aggregate="p95",
    )
```

```bash
mcp-test -m perf          # only @marker(tags including "perf")
mcp-test -k echo        # name filter
```

---

## 4) Snapshots and update mode

```python
# tests/test_snapshots.py
from pathlib import Path

from mcp_test_harness.assertions import assert_snapshot, assert_tool_call

async def test_tool_response_shape(mcp_server):
    result = await assert_tool_call(mcp_server, "get_config", {})
    data = {"content": [c.model_dump() if hasattr(c, "model_dump") else str(c) for c in result.content]}
    await assert_snapshot(
        data,
        "get_config",
        test_file=Path(__file__),
        ignore_fields=None,
    )
```

After intentional output changes: `mcp-test --update-snapshots`

---

## 5) Plugin in config

```yaml
plugins:
  - path/or/module/to/your_plugin.py
```

For a full reference implementation, see [reference_plugin.py](reference_plugin.py) in this folder.
