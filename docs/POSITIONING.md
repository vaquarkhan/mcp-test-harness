# Product positioning — why MCP Test Harness is different

This document explains the **four structural differentiators** that set MCP Test Harness apart from manual inspectors, stochastic fuzzers, LLM evaluators, and generic load tools. For a concise ecosystem map, see [COMPARISON.md](COMPARISON.md).

---

## Executive summary

MCP Test Harness is the **deterministic, CI-native pre-production gate** for MCP servers. It unifies **functional**, **regression**, and **performance** testing in one LLM-free run; abstracts the full **protocol lifecycle** via fixtures; keeps **stateful workflows in Python** (anti-DSL); and publishes a **unified portal** (category scores, coverage gaps, HTML/JSON artifacts) per run.

Use **[mcp-shark](https://github.com/mcp-shark/mcp-shark)** for IDE config security and local traffic forensics. Use **MCP Test Harness** to prove **server behavior** before merge.

---

## Differentiator 1: Deterministic tri-modal CI-native architecture

### The capability

One `mcp-test` run can gate **correctness**, **behavioral regression**, and **performance** without an LLM in the loop.

| Assertion | Role |
|-----------|------|
| `assert_tool_call`, `assert_resource_read`, … | Functional correctness |
| `assert_snapshot`, `assert_tool_idempotent` | Regression / determinism |
| `assert_latency` | Single-call or aggregated p95/p99/mean/median with **warmup** |
| `assert_throughput` | Concurrent load (stateful session): **min_rps**, **max_p99_ms**, **max_error_rate** |
| `assert_stateless_throughput` | Concurrent load (stateless HTTP, SEP-2575): duration × concurrency RPS / p99 / error % |
| `assert_latency_within_baseline` | JSON baseline drift gates (like visual regression for latency) |

In agentic systems, **slow is broken**: a correct tool that returns in ten seconds can still destroy multi-step agent loops. The harness treats latency as a functional requirement inside the same tests that check payloads.

### Why competitors do not combine this

- **Fuzzers** (e.g. Viper-MCP, mcp-testbench) hunt crashes and injections; they do not enforce SLO percentiles during functional runs.
- **LLM evaluators** add model latency and non-determinism; they measure agent behavior, not bare server SLOs.
- **k6 / JMeter / Gatling** generate HTTP load but lack native MCP handshake, capability negotiation, and JSON-RPC schema awareness.

### Example

```python
@marker(tags=["perf"])
async def test_checkout_under_load(mcp_server):
    await assert_tool_call(mcp_server, "reserve", {"sku": "A1"})
    await assert_throughput(
        mcp_server, "reserve", {"sku": "A1"},
        concurrent=8, total_calls=32,
        min_rps=10.0,
        max_p99_ms=500.0,
        max_error_rate=0.02,
    )
```

---

## Differentiator 2: Native protocol-aware fixture system

### The capability

Built-in fixtures **`mcp_server`** (per test) and **`mcp_server_session`** (per module) hide:

1. Subprocess / transport startup (stdio, SSE, HTTP)
2. JSON-RPC **initialize** handshake and capability negotiation
3. Injection of a ready **ClientSession**
4. Graceful teardown and parallel **module grouping** (same-file tests stay on one worker)

Developers write domain logic; the harness orchestrates the stateful protocol lifecycle.

### Why this matters

Raw scripts and curl require manual JSON-RPC envelopes, message IDs, and stdio framing. Fuzzers abstract connections for **predefined attacks**, not arbitrary business tests. **MCP Inspector** is manual and GUI-bound. This harness is **extensible, code-first, and CI-native**.

---

## Differentiator 3: Code-first stateful workflow orchestration (anti-DSL)

### The capability

Multi-step agent workflows (search → extract ID → transact) are written in **async Python**, not a proprietary YAML/JSON collection DSL.

```python
async def test_reserve_then_confirm(mcp_server):
    r1 = await assert_tool_call(mcp_server, "create_hold", {"sku": "A1"})
    hold_id = r1.content[0].text
    await assert_tool_call(mcp_server, "confirm", {"holdId": hold_id})
```

Benefits: typing, IDE support, `@marker(tags=[...])`, PR-reviewable diffs, fixture cycle detection, and the full Python ecosystem for data generation.

Declarative collections remain an **optional** future surface ([COLLECTIONS.md](COLLECTIONS.md)); the default path is Python for stability and speed in CI.

---

## Differentiator 4: Unified pre-production portal

### The capability

Each run produces a **single artifact** with:

- **Category scores** — functional, performance, security, resiliency (from `@marker` tags)
- **Coverage map** — tools advertised vs tested vs missing auth tests
- **Reports** — console, JUnit, JSON, HTML with the unified portal section

Security-tagged tests feed the same report as functional and perf tests — one gate, one narrative for auditors and developers.

---

## Enterprise governance and security

### Schema validation as contract enforcement

With `schema_validation: true` (default), the harness validates `initialize`, `tools/list`, resources/prompts shapes, and a best-effort `schema_probe_call_tool`. This catches **schema–implementation drift** before LLM consumers generate invalid calls.

### Security payload packs (shipped)

Tag tests `@marker(tags=["security"])` and use:

- `assert_injection_blocked` — prompt-injection corpus
- `assert_path_traversal_blocked` — path traversal payloads
- `assert_no_secret_leak` — secret pattern scanner
- `run_security_payload_pack` — combined smoke
- `assert_tool_denied`, `assert_authorization_boundary` — auth boundaries

See [SECURITY_TESTING.md](SECURITY_TESTING.md).

### MCP-Bastion pairing

| Layer | Tool | When |
|-------|------|------|
| CI verification | **MCP Test Harness** | Every PR — behavior, perf, security regressions |
| Runtime defense | **[MCP-Bastion](https://github.com/vaquarkhan/MCP-Bastion)** | Production — injection, PII, rate limits, RBAC |

EU AI Act–aligned demo packs: `examples/feature-demo/eu-ai-act/`.

### Recommended dual-tool CI

```yaml
# Config security (IDE) — optional, Node.js
- run: npx @mcp-shark/mcp-shark scan --ci --format sarif

# Server behavior (CI) — Python
- uses: vaquarkhan/mcp-test-harness/.github/actions/mcp-test@main
```

---

## Conclusion

As organizations scale autonomous agents, manual inspection and volatile LLM evals are insufficient for merge gates. MCP Test Harness enforces **engineering accountability**: the server must be **correct**, **fast enough**, **regression-stable**, and **security-baselined** before production — with evidence in every report.
