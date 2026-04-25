# Scenario 24: Latency and performance assertions

> **Goal:** Use `assert_latency` (single, mean, p95) with warmups; see the perf doc.

| Field | |
| --- | --- |
| **Primary example** | [`../../../docs/PERFORMANCE.md`](../../../docs/PERFORMANCE.md) — *PERFORMANCE.md* |
| **Index** | [Scenarios index](README.md) · [Feature demo](../README.md) · [Examples](../../README.md) · [FEATURES_INDEX](../../FEATURES_INDEX.md) |

Also: `docs/TUTORIAL.md` and `examples/patterns_mcp_test.md` for `-m perf` ideas.

## Try it

1. Install the harness: `pip install mcp-test-harness` (or `pip install -e ".[dev]"` from a clone).
2. Point any sample `mcp-test.yaml` at your real `server.command` (or a stub) and run from the repo root, e.g. `mcp-test --config <file>` (see the linked file for the exact case).

## See also

- [Feature demo — overview, sample report](../README.md)
- [Examples folder](../../README.md)
- [Developer guide](../../../docs/DEVELOPER_GUIDE.md)
