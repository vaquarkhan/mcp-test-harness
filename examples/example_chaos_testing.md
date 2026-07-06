# Protocol-aware chaos testing (`@marker` + `chaos_faults`)

> [!TIP]
> **Feature highlight (v1.3):** inject **delay**, **503**, **truncated responses**, or **schema drift** on `call_tool` for one test — without changing your server code.

Chaos faults wrap the MCP session for tests tagged with `chaos`. Use them to verify **client resilience**, **timeout budgets**, and **contract strictness** before production incidents.

## Enable chaos on a test

```python
from mcp_test_harness import marker
from mcp_test_harness.assertions import assert_tool_call
from mcp_test_harness.chaos import ChaosFaultError

# Injected latency (still passes if timeout allows)
@marker(tags=["chaos", "resiliency"], chaos_faults=["delay_ms:100"])
async def test_survives_slow_gateway(mcp_server):
    await assert_tool_call(mcp_server, "echo", {"text": "slow"})

# Simulated 503 — expect the harness to raise ChaosFaultError
@marker(tags=["chaos", "negative"], chaos_faults=["503"])
async def test_gateway_unavailable(mcp_server):
    try:
        await mcp_server.call_tool("echo", {"text": "x"})
        raise AssertionError("expected simulated 503")
    except ChaosFaultError as exc:
        assert exc.code == 503

# Partial/truncated tool result
@marker(tags=["chaos", "contract"], chaos_faults=["truncate"])
async def test_handles_truncated_payload(mcp_server):
    result = await mcp_server.call_tool("echo", {"text": "long-response-body"})
    assert getattr(result, "content", None)

# JSON schema drift inside tool text payloads
@marker(tags=["chaos", "contract"], chaos_faults=["schema_drift"])
async def test_detects_field_rename(mcp_server):
    result = await mcp_server.call_tool("echo", {"text": '{"user_id": 1}'})
    text = result.content[0].text
    assert "user_id" in text or "id" in text  # drift may rename keys
```

## Fault reference

| Fault | Aliases | Effect |
|-------|---------|--------|
| Delay | `delay`, `slow`, `delay_ms:50`, `delay:200` | `asyncio.sleep` before `call_tool` returns |
| 503 | `error_503`, `unavailable`, `retry_storm` | Raises `ChaosFaultError` (code 503) |
| Truncate | `partial`, `partial_result` | Shortens text in the first content item |
| Schema drift | `drift`, `schema-drift` | Mutates JSON in text payloads (field renames, extra keys) |

You can also use tag shorthand: `@marker(tags=["chaos:truncate"])`.

## Filter chaos tests

```bash
mcp-test -m chaos --server-command "python -m your_server"
```

Combine with **retry** markers when testing recovery:

```python
@marker(tags=["chaos"], chaos_faults=["503"], retry=2, timeout=30)
async def test_retry_on_transient_fault(mcp_server):
    ...
```

## Design notes

- Chaos applies to **`call_tool` only** — list/read/prompt methods pass through unchanged.
- Traces still record chaos-wrapped calls (see [example_mcp_trace.md](example_mcp_trace.md)).
- For **server-side** error bursts without injection, see `assert_reconnects` / `assert_survives_crash` in [docs/SECURITY_TESTING.md](../docs/SECURITY_TESTING.md).

## Runnable demo pack

**[feature-demo/platform-qa/test_platform_qa_demo.py](feature-demo/platform-qa/test_platform_qa_demo.py)** — copy-paste chaos patterns with `-m chaos` filtering.
