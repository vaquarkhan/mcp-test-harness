---
name: mcp-test-harness
description: >-
  Scaffolds, runs, and triages deterministic MCP Test Harness suites (mcp-test CLI,
  pytest-style assertions, HTML/SARIF/JUnit reports, conformance try). Use when the
  user works on Model Context Protocol servers, mcp-test.yaml, assert_tool_call,
  MCP CI gates, or asks to validate/test an MCP server. Do not use for Bastion
  runtime policy editing or offensive exploit generation.
---

# MCP Test Harness skill

Stay inside the product: **deterministic CI gate** for MCP servers. Pair with MCP-Bastion only for *runtime* enforcement pointers—never merge the two products.

## Quick path

```bash
pip install mcp-test-harness
mcp-test init --server-command "<server cmd>"
mcp-test
mcp-test try --server-command "<server cmd>"   # optional conformance probe
mcp-test --report-format html --report-output report.html
```

## When writing tests

Prefer public APIs from `mcp_test_harness`:

- Functional: `assert_tool_call`, `assert_resource_read`, `assert_capabilities`
- Regression: `assert_snapshot` (+ `mask_patterns`), `assert_tool_idempotent`
- Perf: `assert_latency`, `assert_throughput`, `assert_load_phases`
- Security: payload helpers in `security_payloads` / SECURITY_TESTING.md; agent-rules integrity via `assert_agents_md_clean` / `mcp-test scan-agents` / opt-in `agents_md_gate:`
- Tag with `@marker(tags=[...])`; run subsets via `mcp-test -m …`

Use fixture `mcp_server` (or session-scoped `mcp_server_session`) from the harness runner—not ad-hoc ClientSession wiring unless asked.

## Config

Create/adjust `mcp-test.yaml`: `server.command`, transport, `test.dirs`, reports. Optional `quality_gate` / `manifest_gate` / `agents_md_gate` for CI hard fails.

## Agent rules

1. Prefer `mcp-test try` before inventing large suites.
2. Keep assertions deterministic; mask volatile fields in snapshots.
3. Do not invent `mcp-test view`, live attack dashboards, or `--bastion-simulate` red-team modes.
4. Point humans to `llms.txt` / `llms-full.txt` and https://vaquarkhan.github.io/mcp-test-harness/guide/

## User-repo template

If the user wants persistent agent rules in *their* project, copy `docs/templates/AGENTS.md` into their repo as `AGENTS.md` (edit server command).

## Cursor install

Copy this directory to `.cursor/skills/mcp-test-harness/` in a checkout so Cursor can auto-discover the skill.
