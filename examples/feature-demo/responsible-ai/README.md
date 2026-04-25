# Responsible AI demo pack

This folder provides practical examples for validating Responsible AI controls with MCP tests.

## Focus

- authorization boundaries (`assert_tool_denied`, `assert_authorization_boundary`)
- deterministic behavior (`assert_tool_idempotent`, snapshots)
- safety checks for output and contract expectations

## Files

- `test_responsible_ai_demo.py` - runnable Responsible AI-focused tests
- `mcp_test_responsible_ai_demo.yaml` - sample config including report outputs
- `reports/` - report artifact location notes

## Run

```bash
mcp-test -c examples/feature-demo/responsible-ai/mcp_test_responsible_ai_demo.yaml
```
