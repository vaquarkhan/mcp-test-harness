# Snapshot testing

Compare golden files under **`tests/__snapshots__/<name>.snap`**. Use for regression when a tool response shape should stay stable.

- **First run** creates the snapshot; later runs **compare** JSON (with `ignore_fields` and `mask_patterns` for volatile bits).
- **Intentional change:** `mcp-test --update-snapshots`

**Runnable without a server:** [assertions_async_demo.py](assertions_async_demo.py) step 13 (temp `test_*.py` and `__snapshots__`).

**Copy into your tests** (typical project): [patterns_mcp_test.md](patterns_mcp_test.md) (snapshots section)
