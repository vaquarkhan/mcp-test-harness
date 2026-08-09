# MCP Performance Testing Strategy

This page defines product positioning for performance testing in MCP Test Harness.

## Why performance belongs in an MCP harness

MCP servers are not plain HTTP endpoints. A single tool call often includes:

- MCP initialize/session behavior
- JSON-RPC request/response framing
- tool execution
- model inference or external dependencies

Because of that, teams need performance checks in the **same MCP-aware tests** that validate correctness.

If a tool is correct but returns in 10 seconds, the agent loop still fails in practice.

## The position in one line

**MCP Test Harness is one tool for three testing modes:**

1. **Functional:** protocol-aware correctness checks
2. **Regression:** snapshots and determinism
3. **Performance:** latency and SLO-style gates in CI

This is the differentiator versus tools that only provide manual inspection, LLM eval, or standalone benchmarking.

## What is already strong today

- `assert_latency` with `max`, `p90`, `p95`, `p99`, `mean`, `median`
- `warmup` support for cold-start exclusion
- idempotency checks via `assert_tool_idempotent`
- marker-driven filtering (`-m perf`)
- shared session fixture (`mcp_server_session`) so startup overhead does not dominate every test
- **Stateful** `assert_throughput` — fixed burst or closed-loop `duration_s`, `min_rps`, `max_p90_ms` / `max_p95_ms` / `max_p99_ms`, `max_error_rate`, weighted multi-tool `calls`
- **`assert_load_phases`** — concurrency ramp with warmup phases excluded from aggregate gates
- **Stateless** `assert_stateless_throughput` + `mcp-test conformance stateless` (SEP-2575; see [RFC-006](design/RFC-006-stateless-mcp.md))

## Production-grade roadmap (prioritized)

### 1) Throughput assertion — **shipped**

Stateful: `assert_throughput(...)` — concurrent session tool calls with fixed `total_calls` or closed-loop `duration_s`, percentile / RPS / error-rate gates, and optional weighted `calls` mixes.

Ramp: `assert_load_phases(...)` — ordered phases with warmup excluded from aggregate SLOs ([PERFORMANCE.md](PERFORMANCE.md) §4–4.1).

Stateless (2026-07-28): `assert_stateless_throughput(...)` — URL-direct duration × concurrency with `min_rps`, `max_p95_ms`, `max_p99_ms`, `max_error_rate` ([PERFORMANCE.md](PERFORMANCE.md) §4.2).

### 2) Baseline + regression file

Perf baseline support similar to snapshots:

- write baseline JSON
- compare current run vs baseline
- fail when regression exceeds configured percentage
- optional `--update-perf-baseline`

### 3) Histogram in HTML report

Inline SVG histogram for latency distribution (no CDN / no external assets).

### 4) Resource usage checks

Optional `psutil` integration for stdio process:

- RSS memory caps
- CPU usage caps

### 5) Stress/ramp profile — **shipped**

Stage-based load via `assert_load_phases` (increasing concurrency / duration). Further open-loop fixed-RPS pacing remains optional future work.

## In scope vs out of scope

### In scope (harness core)

- MCP-aware assertions
- CI pass/fail thresholds
- protocol-aware performance regression tests

### Out of scope (use dedicated tools)

- multi-host distributed load generation
- network chaos and packet fault injection
- full observability backend and dashboard hosting

The harness should integrate with those systems, not replace them.

## Recommended messaging for README / docs

Use this concise positioning:

> MCP Test Harness gives you protocol-aware **functional**, **regression**, and **performance** testing in one CI-native tool.

That sentence captures the product story and avoids overlap with unrelated benchmarking or observability tools.

## Related strategy docs

- [ROADMAP.md](ROADMAP.md)
- [SECURITY_TESTING.md](SECURITY_TESTING.md)
- [CONTRACT_AND_COMPAT.md](CONTRACT_AND_COMPAT.md)
- [ENTERPRISE_GOVERNANCE.md](ENTERPRISE_GOVERNANCE.md)
- [PLUGIN_REGISTRY.md](PLUGIN_REGISTRY.md)

