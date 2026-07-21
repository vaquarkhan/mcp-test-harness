# Example: Stateless hyperscale throughput (`assert_stateless_throughput`)

> [!TIP]
> **Feature highlight:** protocol-aware load without MCP session handshake. For **stateful** session load, use `assert_throughput(mcp_server, …)` instead — see [PERFORMANCE.md](../docs/PERFORMANCE.md).

## Pytest gate

```python
import pytest
from mcp_test_harness import assert_stateless_throughput, marker


@marker(tags=["perf", "stateless"])
@pytest.mark.asyncio
async def test_tool_under_agent_load():
    await assert_stateless_throughput(
        target_url="http://localhost:8080/mcp",
        tool_name="echo",
        arguments={"message": "load"},
        duration_s=10,
        concurrency=50,
        min_rps=100.0,
        max_p99_ms=200.0,
        max_error_rate=1.0,  # percent of failed requests
    )
```

## Parameters

| Parameter | Meaning |
|-----------|---------|
| `target_url` | Streamable HTTP MCP endpoint |
| `tool_name` / `arguments` | `tools/call` payload |
| `duration_s` | How long workers fire requests |
| `concurrency` | Parallel HTTP workers |
| `min_rps` | Fail if achieved RPS is below this |
| `max_p99_ms` | Fail if p99 latency exceeds this |
| `max_error_rate` | Fail if error % exceeds this (HTTP ≠200 or JSON-RPC `"error"`) |

Each request injects SEP-2575 `_meta` and SEP-2243 `MCP-Protocol-Version` / `Mcp-Method` / `Mcp-Name` headers.

## Stateful counterpart (unchanged)

```python
@marker(tags=["perf"])
async def test_reserve_under_load(mcp_server):
    await assert_throughput(
        mcp_server,
        "reserve",
        {"sku": "A1"},
        concurrent=8,
        total_calls=32,
        min_rps=10.0,
        max_p99_ms=500.0,
        max_error_rate=0.02,
    )
```

Tutorial: [TUTORIAL_STATELESS.md](../docs/TUTORIAL_STATELESS.md) · Demo pack: [feature-demo/stateless-testing/](feature-demo/stateless-testing/README.md)
