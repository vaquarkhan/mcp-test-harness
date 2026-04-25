# Python demo scenarios (30 files)

These are runnable demo tests under `examples/feature-demo/python-scenarios/`, one `.py` per scenario.

## Run all 30 demos

```bash
mcp-test --server-command "python -m your_server" examples/feature-demo/python-scenarios
```

## Run only perf demos

```bash
mcp-test --server-command "python -m your_server" -m perf examples/feature-demo/python-scenarios
```

## Notes

- File names follow your requested matrix:
  - `test_demo_01_assert_tool_call.py` ... `test_demo_30_skip_with_reason.py`
- Update placeholder names (`echo`, `resource://status`, `summarize`) for your server.
- Snapshot demos (`12/13/14`) write snapshots relative to each demo file.

## Regenerate

```bash
python examples/feature-demo/generate_demo_py_files.py
```

**Up:** [Feature demo](../README.md) · [Scenario markdown index](../scenarios/README.md)

