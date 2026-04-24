# Editors: Visual Studio Code, Cursor, and similar

A good editor setup **speeds up** writing and running MCP server tests: YAML config, Python tests, and the **`mcp-test` CLI** in an integrated terminal.

## What this repo already gives you (high value, zero install)

| Asset | Path | What it does |
|-------|------|----------------|
| **Code snippets** | [`.vscode/mcp-test-harness.code-snippets`](../.vscode/mcp-test-harness.code-snippets) | Inserts `assert_tool_call`, `async` test stubs, and common harness patterns. |
| **Docs hub** | [README.md](README.md) in this folder | All guides, adoption paths, and deep links. |

**Visual Studio Code / Cursor:** in the **Command Palette** (*Insert Snippet* or *Snippets: Insert Snippet*), choose a snippet that starts with `mcp-` (names depend on how the editor indexes the file).

Or **copy** the snippets file into your own project’s `.vscode/` and adjust; MIT license applies to this repository.

## Recommended extensions (optional)

These are *not* hard dependencies; they add a lot of value for day-to-day work.

| Extension (marketplace) | Why |
|-------------------------|-----|
| **Python** (Microsoft / anyio-friendly) | Syntax, run/debug tests, venv, `PYTHONPATH=src` for local harness dev. |
| **YAML** (Red Hat) | `mcp-test.yaml` / `mcp-test.yml` with schema-like highlighting and structure. |
| **Even Better TOML** (tamasfe) | If you use `mcp-test.toml` config. |
| **Markdown** (built-in) | Read `docs/*.md` with preview (*Markdown: Open Preview*). **Mermaid** diagrams in this repo (e.g. [ARCHITECTURE.md](ARCHITECTURE.md), [DOCKER.md](DOCKER.md)) **render in GitHub**; in VS Code, install **“Markdown Preview Mermaid Support”** (or open the file on GitHub) to see the diagrams. |

**Cursor** users: the same **VS Code** extension ecosystem and workspace folders apply; your **AI chat** can use the open `docs/DEVELOPER_GUIDE.md` and `mcp-test.yaml` as context for accurate answers.

## Suggested “visual” layout (two panes)

1. **Left:** your test file (`tests/test_*.py`) or `mcp-test.yaml`.
2. **Right:** [QUICK_START.md](QUICK_START.md) or [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) in preview, **or** [ARCHITECTURE.md](ARCHITECTURE.md) to keep the system diagram in view while you write assertions.
3. **Bottom:** **Terminal** with `mcp-test` (or `pytest` only if you wire fixtures yourself; the harness is designed for the **`mcp-test` CLI**).

## Running `mcp-test` from the integrated terminal

```bash
# from repo with config in CWD
mcp-test

# explicit config
mcp-test --config mcp-test.yaml
```

Set **`PYTHONPATH=src`** when developing the **harness** itself (see [CONTRIBUTING.md](../CONTRIBUTING.md)), not when only testing *your* MCP project that depends on the installed package.

**Related:** [Docker](DOCKER.md) for a **headless** `mcp-test` in a container. · [TUTORIAL.md](TUTORIAL.md) for a guided first run.
