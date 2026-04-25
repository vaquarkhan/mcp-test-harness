# Scenario 2: MCP assertion helpers

> **Goal:** Use `assert_tool_call`, snapshots, and related helpers to validate your server.

| Field | |
| --- | --- |
| **Primary example** | [`../../assertions_async_demo.py`](../../assertions_async_demo.py) — *All assert_* in one script (fake session)* |
| **Index** | [Scenarios index](README.md) · [Feature demo](../README.md) · [Examples](../../README.md) · [FEATURES_INDEX](../../FEATURES_INDEX.md) |

See the mapping in [`example_mcp_assertions.md`](../../example_mcp_assertions.md).


## Try it

1. Install the harness: `pip install mcp-test-harness` (or `pip install -e ".[dev]"` from a clone).
2. Point any sample `mcp-test.yaml` at your real `server.command` (or a stub) and run from the repo root, e.g. `mcp-test --config <file>` (see the linked file for the exact case).

## See also

- [Feature demo — overview, sample report](../README.md)
- [Examples folder](../../README.md)
- [Developer guide](../../../docs/DEVELOPER_GUIDE.md)
