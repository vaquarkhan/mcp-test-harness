# `mcp-test init` (scaffold)

Creates a starter **`mcp-test.yaml`** and a **`tests/`** module with harness patterns (`@marker`, `mcp_server`, `assert_tool_list`, …) so you can edit in one place.

```bash
mcp-test init
mcp-test init --server-command "python -m mypackage.mcp"
mcp-test init --help
```

**Then:** set your real `server.command`, remove `@skip` from generated smoke tests, and run `mcp-test`.

**Related:** [QUICK_START.md](../docs/QUICK_START.md)
