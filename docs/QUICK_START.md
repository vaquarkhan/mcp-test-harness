# Quick start

Minimal path from zero to a first automated MCP server test. For the full reference, see [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md). For **CI and report outputs**, see [CI_AND_REPORTS.md](CI_AND_REPORTS.md).

## 1. Install

```bash
pip install mcplint
# or: pip install "mcp-test-harness"   # if published under that name
```

From this repo in editable mode:

```bash
pip install -e ".[dev]"
mcp-test --version
```

## 2. Scaffold a starter (recommended)

In your project root (where you want `tests/` and `mcp-test.yaml`):

```bash
mcp-test init
mcp-test init --server-command "python -m your_package.mcp"
```

This creates a sample test module and config. See `mcp-test init --help` for paths and `--no-config` / `--force`.

## 3. Run the harness

```bash
mcp-test --server-command "python your_mcp_server.py" tests/
```

With a config file in the current directory (e.g. after `mcp-test init`):

```bash
mcp-test
```

## 4. Next steps

- **Performance checks** (latency budgets, p95, tags like `perf`): [PERFORMANCE.md](PERFORMANCE.md)
- **Other MCP tools** (conformance, LLM evals, benchmarks) vs this harness: [COMPARISON.md](COMPARISON.md)
- Assertions and fixtures: [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)
- Longer walkthrough: [TUTORIAL.md](TUTORIAL.md)
- GitHub Action for CI: your repo’s `.github/actions/mcp-test` or the README’s workflow examples

## Related: MCP-Bastion (security)

To **protect** a server in production (not only test it), see [MCP-Bastion](https://github.com/vaquarkhan/MCP-Bastion) — policy-as-code, PII, rate limits, and audit. Test with this harness; run with Bastion in front of untrusted clients.
