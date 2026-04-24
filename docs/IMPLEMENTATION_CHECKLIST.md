# Feature implementation checklist (gap analysis)

This document maps the original improvement list to the codebase. **100% of requested product behavior** is implemented; some items (e.g. sub-package licenses) are out of scope for the core repo.

| # | Request | Status | Where |
|---|---------|--------|--------|
| 1 | Stdio process handle for crash monitoring (not `None`) | **Done** | `stdio_mcp.py` yields process; `transport.py` / `StdioTransportAdapter._process`; `lifecycle._extract_process` |
| 2 | `shlex.split` for stdio server command | **Done** | `transport.py` (`shlex.split`, `posix=…`) |
| 3 | MCP shape validation (initialize, tools/resources/prompts lists, content types) | **Done** | `schema.py` (`validate_*`, `validate_mcp_server_after_connect`); wired in `scheduler` via `_assert_mcp_compliance` when `schema_validation` is true |
| 4 | `validate_tool_schemas` in execution path + optional arg validation in `assert_tool_call` | **Done** | After `list_tools` in `validate_mcp_server_after_connect`; `assert_tool_call(..., validate_against_input_schema=True)` with `jsonschema` |
| 5 | Parallel + per-module fixtures (group by module) | **Done** | `scheduler.run_parallel` module buckets + docs |
| 6 | Surface test module import errors | **Done** | `discovery._load_module_from_path` logs warning + `exc_info` |
| 7 | Fixture cycle detection | **Done** | `FixtureManager._resolving` in `fixtures.py` |
| 8 | `assert_tool_schema` | **Done** | `assertions.py` + `__init__.py` export |
| 9 | Snapshot `ignore_fields` / masking | **Done** | `assert_snapshot` + sorted dicts in `_serialize` |
| 10 | License for CI/commercial use | **Done (core)** | Core `LICENSE` = MIT; `NOTICE`; optional `packages/*` may keep separate metadata |
| — | `assert_tool_call_validates_input`, `assert_protocol_version`, `assert_tool_idempotent`, `assert_latency` | **Done** | `assertions.py` |
| — | `--watch` CLI | **Done** | `cli.py` (`MCP_TEST_HARNESS_WATCH_MAX_OUTER` for tests) |

**Test coverage** for the *framework* source (`src/mcp_test_harness`, excluding the vendored `stdio_mcp` subprocess I/O) is enforced at **100% line** (see `pyproject.toml` `[tool.coverage.*]`). `stdio_mcp.py` is omitted from the strict gate (same file used for real process lifecycle); behavior is still covered indirectly via `transport` + lifecycle tests and manual stdio runs.
