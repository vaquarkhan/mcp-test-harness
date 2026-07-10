# RFC-001: Record session to test suite

## Status

Accepted (v1)

## Summary

Turn a live MCP session (or a JSON cassette of tool calls) into a reviewable
pytest-style suite with real arguments and response snapshots:

```bash
mcp-test record --server-command "python my_server.py" --out tests/test_mcp_recorded.py
mcp-test --config mcp-test.yaml tests/test_mcp_recorded.py
```

## Motivation

`mcp-test generate` invents placeholder args from schemas. Authors still must
hand-craft happy-path payloads. Recording kills that barrier: the same calls you
would type in the [MCP Inspector](https://modelcontextprotocol.io/docs/tools/inspector)
become deterministic CI tests.

This is the Tier 1 “install → first green suite” unlock (see [ROADMAP_GROWTH.md](../ROADMAP_GROWTH.md)).

## Design (v1)

1. **Start** the server with the same lifecycle as `generate` / `try`.
2. **Discover** tools via `tools/list`.
3. **Call** each selected tool with schema-derived example arguments (reuse
   `generate.example_arguments`), or use calls from `--from-json`.
4. **Emit** Python tests:
   - `assert_tool_call(mcp_server, name, args)`
   - `assert_snapshot(result, "recorded_<tool>", test_file=Path(__file__))`
5. **Write** `__snapshots__/recorded_*.snap` during record so the first CI run
   matches (same serialization as `assert_snapshot`).

Tags: `@marker(tags=["smoke", "recorded"])`.

## Non-goals (v1)

- Transport-level VCR / offline fake session (see [CONTRACT_AND_COMPAT.md](../CONTRACT_AND_COMPAT.md)).
- Interactive REPL recording (future: Inspector export → `--from-json`).
- Automatic LLM-authored tests.

## CLI

| Flag | Meaning |
|------|---------|
| `--server-command` / `--config` / `--transport` | Same as generate |
| `--out` | Output test path (default `tests/test_mcp_recorded.py`) |
| `--force` | Overwrite existing file |
| `--tools` | Comma-separated tool name filter |
| `--max-tools` | Cap number of tools recorded |
| `--from-json` | Cassette JSON with `calls: [{tool, arguments, response?}]` |
| `--no-snapshots` | Emit calls only (no `.snap` files) |
| `--session-json` | Also dump raw call/response pairs for debugging |

## Success criteria

- New server author: record → review → `mcp-test` green in minutes.
- 100% unit coverage on `record.py`.
- Documented next to Inspector pairing in [COMPARISON.md](../COMPARISON.md).
