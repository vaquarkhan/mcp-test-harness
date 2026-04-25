# Feature-demo quick run (markdown + python scenarios)

`feature-demo/` now has two parallel learning tracks:

1. **Scenario markdowns** (`scenarios/`) — concept + links
2. **Runnable Python tests** (`python-scenarios/`) — one test file per scenario

## Run all 30 Python scenarios

```bash
mcp-test --server-command "python -m your_server" examples/feature-demo/python-scenarios
```

## Run only perf-tagged demos

```bash
mcp-test --server-command "python -m your_server" -m perf examples/feature-demo/python-scenarios
```

## Run doctor before scenarios

```bash
mcp-test doctor --server-command "python -m your_server"
```

## Explore report output

```bash
mcp-test --server-command "python -m your_server" \
  --report-format html \
  --report-output reports/feature-demo.html \
  examples/feature-demo/python-scenarios
```

