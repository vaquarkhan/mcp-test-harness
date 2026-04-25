# Scenario 22: Version gate (MCP-Bastion / mcplint)

> **Goal:** Enforce a minimum `mcp-bastion-python` and harness line in preflight CI.

| Field | |
| --- | --- |
| **Primary example** | [`../../version_gate.py`](../../version_gate.py) — *version_gate* |
| **Index** | [Scenarios index](README.md) · [Feature demo](../README.md) · [Examples](../../README.md) · [FEATURES_INDEX](../../FEATURES_INDEX.md) |

Requires: `pip install mcp-test-harness[mcplint]` when checking Bastion.

## Try it

1. Install the harness: `pip install mcp-test-harness` (or `pip install -e ".[dev]"` from a clone).
2. Point any sample `mcp-test.yaml` at your real `server.command` (or a stub) and run from the repo root, e.g. `mcp-test --config <file>` (see the linked file for the exact case).

## See also

- [Feature demo — overview, sample report](../README.md)
- [Examples folder](../../README.md)
- [Developer guide](../../../docs/DEVELOPER_GUIDE.md)
