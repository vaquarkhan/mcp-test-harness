# Report artifacts (platform-qa demo)

After running:

```bash
mcp-test -c examples/feature-demo/platform-qa/mcp_test_platform_qa_demo.yaml
```

this folder receives:

| File | Contents |
|------|----------|
| `platform-qa-demo.html` | Full HTML report with **MCP trace timelines** per test |
| `tool-drift.json` | Optional — from `mcp-test generate --drift-report ...` |

Regenerate by re-running the command above against a server with an `echo` tool.
