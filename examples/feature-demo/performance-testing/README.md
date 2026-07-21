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

## Stateless Streamable HTTP (2026-07-28)

For **no-handshake** HTTP load and SEP-2575 certification, see the sibling pack:

- [../stateless-testing/README.md](../stateless-testing/README.md)
- [assert_stateless_throughput example](../../example_stateless_throughput.md)
- [TUTORIAL_STATELESS.md](../../../docs/TUTORIAL_STATELESS.md)