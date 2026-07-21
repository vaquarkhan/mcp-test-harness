# Stateless MCP testing demo pack (SEP-2575)

This folder documents **stateless Streamable HTTP** certification and load testing. Stateful demos remain under [performance-testing/](../performance-testing/README.md) and [functional-testing/](../functional-testing/README.md).

## Files

- `test_stateless_throughput_demo.py` — example pytest using `assert_stateless_throughput` (skipped unless `MCP_STATELESS_URL` is set)
- This README — how to run CLI conformance + the load demo

## Conformance (CLI)

```bash
mcp-test conformance stateless \
  --url "${MCP_STATELESS_URL:-http://localhost:8080/mcp}" \
  --generate-badge
```

## Throughput demo

```bash
# Windows PowerShell
$env:MCP_STATELESS_URL = "http://localhost:8080/mcp"
pytest examples/feature-demo/stateless-testing/test_stateless_throughput_demo.py -q

# macOS / Linux
export MCP_STATELESS_URL=http://localhost:8080/mcp
pytest examples/feature-demo/stateless-testing/test_stateless_throughput_demo.py -q
```

Without `MCP_STATELESS_URL`, the test **skips** so CI for this repo does not depend on a live 2026-07-28 server.

## Docs

- [TUTORIAL_STATELESS.md](../../../docs/TUTORIAL_STATELESS.md)
- [RFC-006](../../../docs/design/RFC-006-stateless-mcp.md)
- [example_stateless_conformance.md](../../example_stateless_conformance.md)
- [example_stateless_throughput.md](../../example_stateless_throughput.md)
