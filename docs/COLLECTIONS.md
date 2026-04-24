# Postman-style collections, environments, and multi-step flows

This document explains how **MCP Test Harness** relates to **Postman collections**, **Newman (CLI)**, and similar **API workflow** tools — and what you can do **today** versus what would be a **future, optional** addition to the `mcp-test` CLI.

---

## What “Postman style” usually means

| Concept | In HTTP / Postman | In MCP + this harness (mental model) |
|--------|-------------------|----------------------------------------|
| **Collection** | Ordered requests in folders: send A, then B using data from A | Ordered **test steps** in one scenario: e.g. `list_tools` → `call_tool("fetch", …)` → `call_tool("commit", {…})` using prior results. |
| **Environment** | Variables: `{{baseUrl}}`, `{{apiKey}}`, different dev/stage/prod | **Python module constants**, a shared **config file** (`mcp-test.yaml` server / transport options), or a **`@fixture`** that provides tokens, paths, or feature flags. |
| **Collection runner** | Postman / Newman runs all requests in order | **Today:** `mcp-test` runs **async test functions** in `tests/` in discovery order, with the **`mcp_server`** (or `mcp_server_session`) fixture. **Not shipped:** a dedicated YAML/JSON “collection file” executed by a `mcp-test collection` subcommand. |
| **Tests on responses** | Status code, body JSON paths, scripts | **Assertions:** `assert_tool_call`, `assert_snapshot`, `assert_tool_schema`, `assert_resource_read`, etc. (see [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)). |
| **Chaining** | `pm.environment.set("id", jsonData.id)` | **Plain Python:** assign a result, pass fields into the next `assert_tool_call` or your own `await session.call_tool(...)`. |

The harness is **MCP + Python**, not HTTP-only — but the *workflow* (group steps, env, chain results, run in CI) is the same product expectation.

---

## What exists in this project today (recommended)

1. **Multi-step flows in one test** — one `async def test_…(mcp_server):`, several calls, use local variables to chain outputs (same idea as a collection folder run linearly).
2. **Environments** — `mcp-test.yaml` / TOML for **server** `command`, **transport** (stdio / `sse` / `http` + [transport options](DEVELOPER_GUIDE.md#part-3-configuration)), time-outs, and [parallel workers](DEVELOPER_GUIDE.md) for **CI**; use OS env vars in `command` or in your server, or fixtures for values you must not hard-code.
3. **Reuse across “collections”** — a Python module of helpers, or the harness **`@fixture`** decorator (see [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md#part-4-fixtures)).
4. **Markers** — tag scenarios (`@marker(tags=["smoke"])`, `perf`, …) and run subsets with `mcp-test -m …` (see [PERFORMANCE.md](PERFORMANCE.md)).
5. **No separate “collection” file format** in the `mcp-test` **CLI** — the **source of truth** for steps is **Python** under `tests/`, which is easier to diff, review, and type-check than a second DSL.

A compact pattern for a **“collection-like”** integration test:

```python
# tests/test_checkout_flow.py
from mcp_test_harness.assertions import assert_tool_call

async def test_reserve_then_confirm(mcp_server):
    r1 = await assert_tool_call(mcp_server, "create_hold", {"sku": "A1", "qty": 1})
    hold_id = _extract_id(r1)  # your small helper, same as saving from a response in Postman
    await assert_tool_call(mcp_server, "confirm", {"holdId": hold_id})
```

This is the supported way to get **“Postman order of operations”** in CI with type safety and normal code review.

---

## Load, throughput, and “collection runner at scale”

- **Single-session latency** and **p95**-style checks are covered by `assert_latency` and [PERFORMANCE.md](PERFORMANCE.md).
- **Many virtual users, sustained RPS, or distributed load** is **out of core**; pair the harness (functional + regression) with **k6**, **JMeter**, **Gatling**, or a cloud load product. See the short note in [COMPARISON.md](COMPARISON.md#postman--or-jmeter-style-ideas-not-in-core-today) and [PERFORMANCE.md](PERFORMANCE.md).

---

## Roadmap: declarative collections (not implemented)

A **Postman / Newman**-like **declarative** layer has been requested (JSON/YAML **steps** + **environments** + optional variable extraction). It is **not** part of a released `mcp-test` yet. If it is added, the intended constraints are (same as stated in the ecosystem [comparison](COMPARISON.md)):

- Shipped as an **optional** path (e.g. `mcp-test run` / `mcp-test collection` for a file), so default **`pytest` + `mcp-test`** CI stays **fast and stable**.
- Composable with existing **assertion** helpers and **schema** checks where possible.

Until then, use **Python tests** for multi-step flows; treat any third-party or internal YAML as **custom tooling** that drives the same public assertion APIs, not a built-in subcommand.

---

## Related documentation

| Topic | Document |
|--------|-----------|
| Full config, transports, parallel, reports | [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) |
| Latency, markers, `mcp-test -m perf` | [PERFORMANCE.md](PERFORMANCE.md) |
| Ecosystem, LLM tools vs this harness, JMeter / load | [COMPARISON.md](COMPARISON.md) |
| Example patterns (markers, yaml stub) | [../examples/patterns_mcp_test.md](../examples/patterns_mcp_test.md) |
