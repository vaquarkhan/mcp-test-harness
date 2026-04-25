# 30 example scenarios (one file each)

| # | File | Focus |
| --- | --- | --- |
| 1 | [scenario_01_test_discovery.md](scenario_01_test_discovery.md) | Test discovery |
| 2 | [scenario_02_mcp_assertions.md](scenario_02_mcp_assertions.md) | All MCP assertions |
| 3 | [scenario_03_fixtures.md](scenario_03_fixtures.md) | Fixtures / `mcp_server` |
| 4 | [scenario_04_schema_validation.md](scenario_04_schema_validation.md) | Schema validation |
| 5 | [scenario_05_snapshots.md](scenario_05_snapshots.md) | Snapshots |
| 6 | [scenario_06_parallel.md](scenario_06_parallel.md) | Parallel workers |
| 7 | [scenario_07_watch.md](scenario_07_watch.md) | Watch mode |
| 8 | [scenario_08_markers.md](scenario_08_markers.md) | Markers / skip |
| 9 | [scenario_09_report_junit.md](scenario_09_report_junit.md) | JUnit report |
| 10 | [scenario_10_report_json.md](scenario_10_report_json.md) | JSON report |
| 11 | [scenario_11_report_html.md](scenario_11_report_html.md) | HTML dashboard report |
| 12 | [scenario_12_plugins.md](scenario_12_plugins.md) | Plugins |
| 13 | [scenario_13_transport_stdio.md](scenario_13_transport_stdio.md) | Stdio transport |
| 14 | [scenario_14_transport_sse.md](scenario_14_transport_sse.md) | SSE |
| 15 | [scenario_15_transport_http.md](scenario_15_transport_http.md) | HTTP |
| 16 | [scenario_16_github_action.md](scenario_16_github_action.md) | GitHub Action |
| 17 | [scenario_17_docker.md](scenario_17_docker.md) | Docker / OCI |
| 18 | [scenario_18_pyinstaller.md](scenario_18_pyinstaller.md) | PyInstaller binary |
| 19 | [scenario_19_mcp_init.md](scenario_19_mcp_init.md) | `mcp-test init` |
| 20 | [scenario_20_cli_filters.md](scenario_20_cli_filters.md) | CLI filters |
| 21 | [scenario_21_config_validation.md](scenario_21_config_validation.md) | Config validation |
| 22 | [scenario_22_version_gate.md](scenario_22_version_gate.md) | Version / mcplint |
| 23 | [scenario_23_basic_usage.md](scenario_23_basic_usage.md) | Python `basic_usage` |
| 24 | [scenario_24_assert_latency.md](scenario_24_assert_latency.md) | Latency / perf |
| 25 | [scenario_25_assert_capabilities.md](scenario_25_assert_capabilities.md) | `assert_capabilities` |
| 26 | [scenario_26_assert_resource.md](scenario_26_assert_resource.md) | `assert_resource_read` |
| 27 | [scenario_27_assert_prompt.md](scenario_27_assert_prompt.md) | `assert_prompt` |
| 28 | [scenario_28_assert_tool_schema.md](scenario_28_assert_tool_schema.md) | `assert_tool_schema` |
| 29 | [scenario_29_assert_protocol_version.md](scenario_29_assert_protocol_version.md) | `assert_protocol_version` |
| 30 | [scenario_30_assert_idempotent.md](scenario_30_assert_idempotent.md) | `assert_tool_idempotent` |

To regenerate the scenario markdowns after editing the table in [generate_scenario_docs.py](generate_scenario_docs.py) (only when you add or renumber scenarios), run from the repository root:

```bash
python examples/feature-demo/scenarios/generate_scenario_docs.py
```

**Hub:** [Feature demo (overview)](../README.md) · [Examples folder](../../README.md) · [Core features index](../../FEATURES_INDEX.md)

Runnable `.py` equivalents of these 30 scenarios are in [../python-scenarios/README.md](../python-scenarios/README.md).

Need a fast execution path? See [../example_feature_demo_quick_run.md](../example_feature_demo_quick_run.md).
