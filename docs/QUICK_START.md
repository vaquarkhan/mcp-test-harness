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

- **Coding agents:** [llms.txt](../llms.txt) · skill [`skills/mcp-test-harness`](../skills/mcp-test-harness/SKILL.md) · paste [templates/AGENTS.md](templates/AGENTS.md) into your app repo · keep rules clean with `mcp-test scan-agents`
- **Performance checks** (latency budgets, p90/p95/p99, throughput / load phases, tags like `perf`): [PERFORMANCE.md](PERFORMANCE.md)
- **Stateless MCP (2026-07-28)** — `mcp-test conformance stateless` + `assert_stateless_throughput`: [TUTORIAL_STATELESS.md](TUTORIAL_STATELESS.md) · [RFC-006](design/RFC-006-stateless-mcp.md)
- **Other MCP tools** (conformance, LLM evals, benchmarks) vs this harness: [COMPARISON.md](COMPARISON.md)
- Assertions and fixtures: [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)
- Longer walkthrough (stateful): [TUTORIAL.md](TUTORIAL.md)
- GitHub Action for CI: your repo’s `.github/actions/mcp-test` or the README’s workflow examples

## Related: MCP-Bastion (security)

To **protect** a server in production (not only test it), see [MCP-Bastion](https://github.com/vaquarkhan/MCP-Bastion) — policy-as-code, PII, rate limits, and audit. Test with this harness; run with Bastion in front of untrusted clients.

CI security packs (injection, Suite A egress/covert, capability reduction): [SECURITY_TESTING.md](SECURITY_TESTING.md) · tutorial: [TUTORIAL.md](TUTORIAL.md#security-payload-packs-suite-a).
