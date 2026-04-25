# Scenario 18: Standalone binary (PyInstaller)

> **Goal:** Ship a single executable for environments without Python.

| Field | |
| --- | --- |
| **Primary example** | [`../../example_pyinstaller.md`](../../example_pyinstaller.md) — *PyInstaller* |
| **Index** | [Scenarios index](README.md) · [Feature demo](../README.md) · [Examples](../../README.md) · [FEATURES_INDEX](../../FEATURES_INDEX.md) |


## Try it

1. Install the harness: `pip install mcp-test-harness` (or `pip install -e ".[dev]"` from a clone).
2. Point any sample `mcp-test.yaml` at your real `server.command` (or a stub) and run from the repo root, e.g. `mcp-test --config <file>` (see the linked file for the exact case).

## See also

- [Feature demo — overview, sample report](../README.md)
- [Examples folder](../../README.md)
- [Developer guide](../../../docs/DEVELOPER_GUIDE.md)
