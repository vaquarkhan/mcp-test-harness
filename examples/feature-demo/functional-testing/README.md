# Functional testing demo pack

This folder contains beginner-friendly **functional MCP tests** that validate expected behavior and protocol correctness.

## Files

- `test_functional_demo.py` - common functional checks (tools, resources, prompts, schema)
- `mcp_test_functional_demo.yaml` - sample config for local runs
- `reports/` - demo report artifacts and generation commands

## Run

```bash
mcp-test --server-command "python -m your_server" examples/feature-demo/functional-testing/test_functional_demo.py
```

Or with the sample config:

```bash
mcp-test -c examples/feature-demo/functional-testing/mcp_test_functional_demo.yaml
```
