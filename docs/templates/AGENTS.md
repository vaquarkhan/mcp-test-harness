# AGENTS.md — MCP Test Harness (paste into your MCP server repo)

Copy this file to your project root as `AGENTS.md` (or merge into an existing one).
It tells coding agents to keep using the **deterministic** MCP Test Harness CI gate.

## Stack

- Test runner: [`mcp-test-harness`](https://github.com/vaquarkhan/mcp-test-harness) (`mcp-test` CLI)
- Runtime security (separate): [MCP-Bastion](https://github.com/vaquarkhan/MCP-Bastion) — do not confuse with CI tests

## Default workflow

1. Install: `pip install mcp-test-harness`
2. Config: `mcp-test.yaml` with `server.command` pointing at this project's MCP server
3. Tests live under `tests/` as async pytest-style functions using harness fixtures/assertions
4. Local: `mcp-test` or `mcp-test try --server-command "…"`
5. Reports: `mcp-test --report-format html --report-output report.html`
6. CI: run `mcp-test` on PRs; upload JUnit / SARIF / HTML artifacts

## Rules for agents editing this repo

- Prefer `assert_tool_call` / `assert_snapshot` / `assert_latency` over raw JSON-RPC scripts
- Keep tests deterministic; use snapshot `mask_patterns` for timestamps/ids
- Tag perf/security tests (`@marker(tags=["perf"|"security"])`) and document how to filter with `-m`
- Do not replace the harness with one-off Inspector sessions for CI
- Do not add autonomous red-team / exploit-PoC frameworks as a substitute for this gate
- Keep this file free of hidden Unicode (zero-width, Tags-block, bidi overrides). CI: `mcp-test scan-agents` or `assert_agents_md_clean()`

## Agent discoverability

Harness machine docs: https://vaquarkhan.github.io/mcp-test-harness/llms.txt  
Full context: https://vaquarkhan.github.io/mcp-test-harness/llms-full.txt  
Handbook: https://vaquarkhan.github.io/mcp-test-harness/guide/handbook.html
