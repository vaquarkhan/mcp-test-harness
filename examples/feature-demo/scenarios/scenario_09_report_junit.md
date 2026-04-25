# Scenario 9: JUnit XML report

> **Goal:** Emit XML for GitHub, Jenkins, or GitLab job summaries.

| Field | |
| --- | --- |
| **Primary example** | [`../../mcp_test_report_junit.yaml`](../../mcp_test_report_junit.yaml) — *Sample `mcp-test.yaml`* |
| **Index** | [Scenarios index](README.md) · [Feature demo](../README.md) · [Examples](../../README.md) · [FEATURES_INDEX](../../FEATURES_INDEX.md) |

Run with `mcp-test --config examples/mcp_test_report_junit.yaml` after pointing `server.command` at your server.

## Try it

1. Install the harness: `pip install mcp-test-harness` (or `pip install -e ".[dev]"` from a clone).
2. Point any sample `mcp-test.yaml` at your real `server.command` (or a stub) and run from the repo root, e.g. `mcp-test --config <file>` (see the linked file for the exact case).

## See also

- [Feature demo — overview, sample report](../README.md)
- [Examples folder](../../README.md)
- [Developer guide](../../../docs/DEVELOPER_GUIDE.md)
