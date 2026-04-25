# Scenario 11: HTML report (human dashboard)

> **Goal:** A self-contained HTML file with pass/fail mix and quality-style summary; ideal for local review or CI artifacts.

| Field | |
| --- | --- |
| **Primary example** | [`../../mcp_test_report_html.yaml`](../../mcp_test_report_html.yaml) — *Sample `mcp-test.yaml`* |
| **Index** | [Scenarios index](README.md) · [Feature demo](../README.md) · [Examples](../../README.md) · [FEATURES_INDEX](../../FEATURES_INDEX.md) |

Open a built sample: [`../reports/sample_mcp_test_report.html`](../reports/sample_mcp_test_report.html) (see [`../reports/README.md`](../reports/README.md)).


## Try it

1. Install the harness: `pip install mcp-test-harness` (or `pip install -e ".[dev]"` from a clone).
2. Point any sample `mcp-test.yaml` at your real `server.command` (or a stub) and run from the repo root, e.g. `mcp-test --config <file>` (see the linked file for the exact case).

## See also

- [Feature demo — overview, sample report](../README.md)
- [Examples folder](../../README.md)
- [Developer guide](../../../docs/DEVELOPER_GUIDE.md)
