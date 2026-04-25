# EU AI Act demo pack

This folder contains example MCP tests aligned with practical EU AI Act evidence needs (technical robustness, traceability, and change-control verification).

## Focus

- robustness checks for protected operations
- deterministic behavior and regression stability
- auditable report outputs for governance workflows

## Files

- `test_eu_ai_act_demo.py` - runnable EU AI Act-aligned test examples
- `mcp_test_eu_ai_act_demo.yaml` - sample config with report outputs
- `reports/` - report artifact location notes

## Run

```bash
mcp-test -c examples/feature-demo/eu-ai-act/mcp_test_eu_ai_act_demo.yaml
```
