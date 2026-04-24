# Examples (MCP Test Harness)

> [!NOTE]
> **Feature highlights** in this folder use [GitHub-style alerts](https://github.blog/changelog/2022-10-20-markdown-alerts-are-now-repositories/) and bold labels. See [../docs/MARKDOWN_CONVENTIONS.md](../docs/MARKDOWN_CONVENTIONS.md) for the full pattern.

All paths are relative to the **repository root**. Install once:

```bash
pip install -e ".[dev]"
# Optional: mcp-bastion extras are only needed for mcplint / version_gate
```

## One example per core feature (checklist)

Start here: **[FEATURES_INDEX.md](FEATURES_INDEX.md)** — maps each [README Core feature](../README.md#core-features) row to **one** primary example (markdown, YAML, or Python).

| Focus | Files |
|-------|--------|
| **Test discovery** | [example_test_discovery.md](example_test_discovery.md) |
| **All `assert_*` helpers** | [assertions_async_demo.py](assertions_async_demo.py) · [example_mcp_assertions.md](example_mcp_assertions.md) (lookup table) |
| **Fixtures** | [example_fixture_system.md](example_fixture_system.md) · [reference_plugin.py](reference_plugin.py) |
| **Schema validation** | [example_schema_validation.md](example_schema_validation.md) |
| **Snapshots** | [example_snapshot_testing.md](example_snapshot_testing.md) |
| **Parallel** | [example_parallel_workers.md](example_parallel_workers.md) · [sample_mcp_test.yaml](sample_mcp_test.yaml) |
| **Watch mode** | [example_watch_mode.md](example_watch_mode.md) |
| **Markers / skip** | [example_markers_skip.md](example_markers_skip.md) · [patterns_mcp_test.md](patterns_mcp_test.md) |
| **Reports** | [example_report_formats.md](example_report_formats.md) · [mcp_test_report_junit.yaml](mcp_test_report_junit.yaml) · [mcp_test_report_json.yaml](mcp_test_report_json.yaml) · [mcp_test_report_html.yaml](mcp_test_report_html.yaml) |
| **Plugins** | [reference_plugin.py](reference_plugin.py) |
| **Transports** | [example_transports.md](example_transports.md) · [mcp_test_transport_sse.example.yaml](mcp_test_transport_sse.example.yaml) · [mcp_test_transport_http.example.yaml](mcp_test_transport_http.example.yaml) |
| **GitHub Action** | [example_github_actions.md](example_github_actions.md) |
| **Docker** | [example_docker.md](example_docker.md) |
| **PyInstaller binary** | [example_pyinstaller.md](example_pyinstaller.md) |
| **`mcp-test init`** | [example_mcp_test_init.md](example_mcp_test_init.md) |
| **CLI `--list`, `-k`, `-m`** | [example_cli_list_filters.md](example_cli_list_filters.md) |

## Runnable scripts

| Script | Run |
|--------|-----|
| [basic_usage.py](basic_usage.py) | `python examples/basic_usage.py` — imports, version, printed list of assertion names |
| [version_gate.py](version_gate.py) | `python examples/version_gate.py` — minimum versions for CI |
| [assertions_async_demo.py](assertions_async_demo.py) | `python examples/assertions_async_demo.py` — all `assert_*` on a fake session |
| [validate_mcp_test_config.py](validate_mcp_test_config.py) | `python examples/validate_mcp_test_config.py [file.yaml]` |

## Other

| File | Notes |
|------|--------|
| [sample_mcp_test.yaml](sample_mcp_test.yaml) | Full sample (stdio, parallel, JUnit) |
| [patterns_mcp_test.md](patterns_mcp_test.md) | Copy-paste: yaml, markers, perf, snapshots |
| [reference_plugin.py](reference_plugin.py) | Complete plugin (assertion + fixture + reporter) — add under `plugins:` |

**Using a real server:** set `server.command` (or `mcp-test --server-command "…"`) and put tests under `tests/` — [QUICK_START.md](../docs/QUICK_START.md).

**Postman-style multi-step flows:** [COLLECTIONS.md](../docs/COLLECTIONS.md).

**Working on the harness source:** [DEVELOPER.md](../docs/DEVELOPER.md).
