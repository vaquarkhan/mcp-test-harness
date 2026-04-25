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

- `assert_latency` with `max`, `p95`, `p99`, `mean`, `median`
- `warmup` support for cold-start exclusion
- idempotency checks via `assert_tool_idempotent`
- marker-driven filtering (`-m perf`)
- shared session fixture (`mcp_server_session`) so startup overhead does not dominate every test

## Production-grade roadmap (prioritized)

### 1) Throughput assertion (highest impact)

Add `assert_throughput(...)` for concurrency-aware regression gates:

- `concurrency`
- `duration_s`
- `min_rps`
- `max_p99_ms`
- `max_error_rate`

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

### 5) Stress/ramp profile

Stage-based load assertions to find breakpoints under increasing concurrency.

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

- [CONTRIBUTING.md](../CONTRIBUTING.md#maintainer-delivery-plan) (maintainer delivery plan)
- [SECURITY_TESTING.md](SECURITY_TESTING.md)
- [CONTRACT_AND_COMPAT.md](CONTRACT_AND_COMPAT.md)
- [ENTERPRISE_GOVERNANCE.md](ENTERPRISE_GOVERNANCE.md)
- [PLUGIN_REGISTRY.md](PLUGIN_REGISTRY.md)

