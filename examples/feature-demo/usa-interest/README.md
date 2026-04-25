# USA interest demo pack

This folder demonstrates MCP tests aligned to U.S. strategic priorities: data protection, authorization control, and audit-ready validation.

## Focus

- "confused deputy" prevention via per-operation deny checks
- sovereignty-oriented data access boundaries (least privilege patterns)
- repeatable CI evidence through structured reports

## Files

- `test_usa_interest_demo.py` - runnable U.S.-interest security examples
- `mcp_test_usa_interest_demo.yaml` - sample config including report outputs
- `reports/` - report artifact location notes

## Run

```bash
mcp-test -c examples/feature-demo/usa-interest/mcp_test_usa_interest_demo.yaml
```
