# Standalone binary (no Python on the target)

From a dev install of this repository:

```bash
pip install -e ".[dev]"
python scripts/build_binary.py
dist/mcp-test --version
```

The spec lives in [mcp_test_harness.spec](https://github.com/vaquarkhan/mcp-test-harness/blob/main/mcp_test_harness.spec) at the repository root. **Platform:** build on the OS you need to support (Windows / Linux / macOS).

**Related:** [README – Standalone binary](../README.md#standalone-binary)
