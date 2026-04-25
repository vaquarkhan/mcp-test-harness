# One example per product feature (README *Core features*)

> [!TIP]
> **Feature highlight:** this page maps each [README *Core features*](../README.md#core-features) row to **one** primary example. For how we style “feature” callouts in Markdown, see [../docs/MARKDOWN_CONVENTIONS.md](../docs/MARKDOWN_CONVENTIONS.md).

Use this as a **checklist** so every [README Core features](../README.md#core-features) row has a **dedicated** example (markdown, YAML, or Python). Assertion helpers that share [assertions_async_demo.py](assertions_async_demo.py) are listed in [example_mcp_assertions.md](example_mcp_assertions.md).

| # | Core feature (README) | Example to open |
|---|------------------------|-----------------|
| 1 | **Test discovery** | [example_test_discovery.md](example_test_discovery.md) |
| 2 | **MCP assertions** (all `assert_*`) | [assertions_async_demo.py](assertions_async_demo.py) + [example_mcp_assertions.md](example_mcp_assertions.md) (mapping table) |
| 3 | **Fixture system** | [example_fixture_system.md](example_fixture_system.md) · built-ins + [reference_plugin.py](reference_plugin.py) (plugin-registered) |
| 4 | **Schema validation** | [example_schema_validation.md](example_schema_validation.md) |
| 5 | **Snapshot testing** | [assertions_async_demo.py](assertions_async_demo.py) (step 13) + [example_snapshot_testing.md](example_snapshot_testing.md) |
| 6 | **Parallel execution** | [example_parallel_workers.md](example_parallel_workers.md) · [sample_mcp_test.yaml](sample_mcp_test.yaml) |
| 7 | **Watch mode** | [example_watch_mode.md](example_watch_mode.md) |
| 8 | **Markers** | [example_markers_skip.md](example_markers_skip.md) · [patterns_mcp_test.md](patterns_mcp_test.md) |
| 9 | **Reports** | [example_report_formats.md](example_report_formats.md) · `mcp_test_report_*.yaml` in this folder |
| 10 | **Plugin system** | [reference_plugin.py](reference_plugin.py) |
| 11 | **Transport** (stdio / SSE / HTTP) | [example_transports.md](example_transports.md) · [sample_mcp_test.yaml](sample_mcp_test.yaml) (stdio) · [mcp_test_transport_sse.example.yaml](mcp_test_transport_sse.example.yaml) · [mcp_test_transport_http.example.yaml](mcp_test_transport_http.example.yaml) |
| 12 | **GitHub Action** | [example_github_actions.md](example_github_actions.md) |
| 13 | **Docker** | [example_docker.md](example_docker.md) |
| 14 | **Standalone binary** | [example_pyinstaller.md](example_pyinstaller.md) |

**30 scenarios (one markdown each):** [feature-demo/scenarios/README.md](feature-demo/scenarios/README.md) — under [feature-demo](feature-demo/README.md) with a sample HTML report; training-style index for discovery, reports, transports, Docker, and every major assertion style.

**Three testing-type demo packs:** [feature-demo/functional-testing/README.md](feature-demo/functional-testing/README.md) · [feature-demo/regression-testing/README.md](feature-demo/regression-testing/README.md) · [feature-demo/performance-testing/README.md](feature-demo/performance-testing/README.md) — separate runnable examples and report configs for each core testing type.

**Security and policy demo packs:** [feature-demo/responsible-ai/README.md](feature-demo/responsible-ai/README.md) · [feature-demo/usa-interest/README.md](feature-demo/usa-interest/README.md) — examples for authorization boundaries, confused-deputy checks, and governance-aligned reporting.

**Also useful (not a separate “core” row):** [example_mcp_test_init.md](example_mcp_test_init.md) (`mcp-test init`) · [example_cli_list_filters.md](example_cli_list_filters.md) (`--list`, `-k`, `-m`) · [example_doctor.md](example_doctor.md) (`mcp-test doctor`) · [example_enhanced_reports.md](example_enhanced_reports.md) (HTML/JSON/JUnit enriched outputs) · [feature-demo/example_feature_demo_quick_run.md](feature-demo/example_feature_demo_quick_run.md) · [validate_mcp_test_config.py](validate_mcp_test_config.py) · [version_gate.py](version_gate.py) · [basic_usage.py](basic_usage.py) (mcplint) · [COLLECTIONS.md](../docs/COLLECTIONS.md) (Postman-style flows)
