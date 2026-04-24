# Test discovery (one file per product feature)

The harness **discovers** `test_*.py` and `*_test.py` under your configured `test.dirs` (default `tests/`). Tests are async functions **named** `test_something` that take **`mcp_server`** (or other registered fixtures) as parameters.

**Rules (short):**
- **File name:** `test_something.py` or `api_test.py`
- **Test function name:** `def test_...` or `async def test_...`
- A file that **fails to import** logs a **warning** and is skipped; check logs in CI
- **List without running:** `mcp-test --list` (see [example_cli_list_filters.md](example_cli_list_filters.md))

**Try it in this repository** (from repo root, with a real `server.command` in `mcp-test.yaml` or use `--server-command`):

```bash
mcp-test --list
mcp-test -k smoke
```

**Related:** [DEVELOPER_GUIDE.md – discovery](../docs/DEVELOPER_GUIDE.md#part-2-project-structure) · [validate_mcp_test_config.py](validate_mcp_test_config.py) for config files before you run
