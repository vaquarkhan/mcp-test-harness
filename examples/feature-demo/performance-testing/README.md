# Performance testing demo pack

This folder contains **performance-focused MCP tests** using latency assertions and SLO-style thresholds.

## Files

- `test_performance_demo.py` - latency checks with p95/p99/mean/median examples
- `mcp_test_performance_demo.yaml` - sample config for perf runs
- `reports/` - demo report artifacts and generation commands

## Run

```bash
mcp-test --server-command "python -m your_server" examples/feature-demo/performance-testing/test_performance_demo.py
```

Or with the sample config:

```bash
mcp-test -c examples/feature-demo/performance-testing/mcp_test_performance_demo.yaml
```
