# `mcp-test generate` (schema-driven test scaffolding)

> [!TIP]
> **Feature highlight (v1.3):** connect to a live server, read `tools/list`, and **draft** Python tests for human review — not auto-merge to `main` without inspection.

`mcp-test generate` is an **offline artifact** workflow: it writes a `test_mcp_generated.py` (or custom filename) with happy-path and stub edge-case tests per tool.

## Basic usage

```bash
# Uses mcp-test.yaml server.command if present
mcp-test generate

# Explicit server + output location
mcp-test generate \
  --server-command "python -m your_server" \
  --dir . \
  --tests-subdir tests \
  --filename test_mcp_generated.py
```

## Typical workflow

1. **`mcp-test doctor`** — confirm the server starts and lists tools.
2. **`mcp-test generate`** — write draft tests.
3. **Review** — remove `@skip`, fix argument examples, add real assertions.
4. **`mcp-test`** — run the reviewed suite in CI.

## Options

| Flag | Purpose |
|------|---------|
| `--config` | Load `server.command` from YAML/TOML |
| `--force` | Overwrite existing output file |
| `--no-edge-cases` | Skip generated `assert_tool_rejects` stubs |
| `--drift-report path.json` | Compare live tools to an existing generated file |

## Drift detection (tools added/removed)

When the output file already exists, generate **refuses to overwrite** unless `--force`. Use drift report to see gaps:

```bash
mcp-test generate \
  --server-command "python -m your_server" \
  --drift-report reports/tool-drift.json
```

Example drift JSON:

```json
{
  "tools_advertised": ["echo", "search", "summarize"],
  "existing_file": "tests/test_mcp_generated.py",
  "tools_missing_from_tests": ["summarize"],
  "drift_detected": true
}
```

## Sample generated output

See **[feature-demo/platform-qa/sample_mcp_generated.example.py](feature-demo/platform-qa/sample_mcp_generated.example.py)** for the shape of generated code (static file — no server required to read it).

Minimal excerpt:

```python
from mcp_test_harness import assert_tool_call, assert_tool_rejects, marker, skip

@marker(tags=["smoke", "generated"])
async def test_tool_echo_happy_path(mcp_server) -> None:
    """Happy-path call for tool ``echo``."""
    await assert_tool_call(mcp_server, "echo", {"text": "example_text"})

@skip(reason='Generated edge case — tailor invalid payload')
@marker(tags=['generated', 'edge'])
async def test_tool_echo_rejects_bad_input(mcp_server) -> None:
    await assert_tool_rejects(mcp_server, "echo", {"__invalid__": True})
```

## Generate against the harness dogfood server

From the repository root (uses bundled fixture server):

```bash
mcp-test generate \
  --server-command "python tests/fixtures/minimal_mcp_server.py" \
  --tests-subdir /tmp/mcp-gen-demo \
  --filename test_mcp_generated.py \
  --force
```

## Why not fully automatic?

Generated tests use **schema-derived placeholder arguments**. They are a **starting point** — tool semantics, auth, and side effects still need human review. See [docs/LLM_TEST_GENERATION.md](../docs/LLM_TEST_GENERATION.md) for the same principle applied to LLM drafts.

**Related:** [example_doctor.md](example_doctor.md) · [example_mcp_test_init.md](example_mcp_test_init.md)
