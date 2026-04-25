# Feature-demo quick run (markdown + python scenarios)

`feature-demo/` now has two parallel learning tracks:

1. **Scenario markdowns** (`scenarios/`) — concept + links
2. **Runnable Python tests** (`python-scenarios/`) — one test file per scenario

It also has three **separate test-type demo packs**:

- `functional-testing/`
- `regression-testing/`
- `performance-testing/`
- `responsible-ai/`
- `usa-interest/`
- `eu-ai-act/`

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

## Run each test type pack with reports

```bash
mcp-test -c examples/feature-demo/functional-testing/mcp_test_functional_demo.yaml
mcp-test -c examples/feature-demo/regression-testing/mcp_test_regression_demo.yaml
mcp-test -c examples/feature-demo/performance-testing/mcp_test_performance_demo.yaml
mcp-test -c examples/feature-demo/responsible-ai/mcp_test_responsible_ai_demo.yaml
mcp-test -c examples/feature-demo/usa-interest/mcp_test_usa_interest_demo.yaml
mcp-test -c examples/feature-demo/eu-ai-act/mcp_test_eu_ai_act_demo.yaml
```

