# Regression testing demo pack

This folder contains **regression-focused MCP tests** for snapshots and idempotency to catch behavioral drift between releases.

## Files

- `test_regression_demo.py` - snapshot and deterministic behavior checks
- `mcp_test_regression_demo.yaml` - sample config for regression runs
- `reports/` - demo report artifacts and generation commands

## Run

```bash
mcp-test --server-command "python -m your_server" examples/feature-demo/regression-testing/test_regression_demo.py
```

Or with the sample config:

```bash
mcp-test -c examples/feature-demo/regression-testing/mcp_test_regression_demo.yaml
```
