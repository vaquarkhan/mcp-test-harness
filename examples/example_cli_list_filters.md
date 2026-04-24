# CLI: list, name filter, marker filter

| Flag | Purpose |
|------|---------|
| `mcp-test --list` | Print discovered `path::test_name` and exit (no server start for listing only — but config still needed for test roots) |
| `mcp-test -k name` | Substring (or `*` / `?` glob) against test names |
| `mcp-test -m tag` | Run tests whose **marker** or **tag** matches (e.g. `smoke`, `perf`) |
| `mcp-test .` or `mcp-test tests/test_api.py` | Run one directory or file |

**Examples:**

```bash
mcp-test --list
mcp-test -k echo
mcp-test -m smoke
mcp-test -m perf tests/test_perf.py
```

**Config + CLI** precedence is documented in [DEVELOPER_GUIDE.md – CLI](../docs/DEVELOPER_GUIDE.md#mcp-test-cli-flags-reference).
