# Scenario 21: Validate `mcp-test.yaml` without running tests

> **Goal:** Fail fast on bad configuration in CI with a small script.

| Field | |
| --- | --- |
| **Primary example** | [`../../validate_mcp_test_config.py`](../../validate_mcp_test_config.py) — *Validator* |
| **Index** | [Scenarios index](README.md) · [Feature demo](../README.md) · [Examples](../../README.md) · [FEATURES_INDEX](../../FEATURES_INDEX.md) |

Run: `python examples/validate_mcp_test_config.py path/to/mcp-test.yaml`.

## Try it

1. Install the harness: `pip install mcp-test-harness` (or `pip install -e ".[dev]"` from a clone).
2. Point any sample `mcp-test.yaml` at your real `server.command` (or a stub) and run from the repo root, e.g. `mcp-test --config <file>` (see the linked file for the exact case).

## See also

- [Feature demo — overview, sample report](../README.md)
- [Examples folder](../../README.md)
- [Developer guide](../../../docs/DEVELOPER_GUIDE.md)
