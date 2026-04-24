# Watch mode (re-run on test file changes)

```bash
mcp-test --watch
```

**Environment (optional):**
- **`MCP_TEST_HARNESS_WATCH_INTERVAL`** — poll interval in seconds
- **`MCP_TEST_HARNESS_WATCH_DEBOUNCE`** — coalesce rapid saves

The watcher monitors `*.py` under your configured test directories (and respects your server command the same as a normal run).

**Note:** on very large trees, use a **narrow** `test_path` or `test.dirs` in config to limit scanning.
