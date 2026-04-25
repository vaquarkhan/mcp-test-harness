"""Regenerate the 30 scenario markdown files. Run from repo root:

    python examples/feature-demo/scenarios/generate_scenario_docs.py
"""

from __future__ import annotations

import os
import textwrap
from pathlib import Path

# (slug, title, one_line_goal, see_file, see_label, extra_lines)
# see_file: path relative to repository root
SCENARIOS: list[tuple[str, str, str, str, str, str]] = [
    (
        "01_test_discovery",
        "Test discovery",
        "How `mcp-test` finds `test_*.py` and test functions the way you expect in CI.",
        "examples/example_test_discovery.md",
        "Walkthrough",
        "",
    ),
    (
        "02_mcp_assertions",
        "MCP assertion helpers",
        "Use `assert_tool_call`, snapshots, and related helpers to validate your server.",
        "examples/assertions_async_demo.py",
        "All assert_* in one script (fake session)",
        "",
    ),
    (
        "03_fixtures",
        "Fixtures and `mcp_server`",
        "Built-in fixtures, dependency order, and custom fixtures in Python tests.",
        "examples/example_fixture_system.md",
        "Fixture system",
        "",
    ),
    (
        "04_schema_validation",
        "Server schema validation",
        "Turn on JSON-RPC and list-shape checks when `schema_validation: true` in config.",
        "examples/example_schema_validation.md",
        "Schema guide",
        "",
    ),
    (
        "05_snapshots",
        "Snapshot and diff on failure",
        "Stable `assert_snapshot` with masks for unstable fields.",
        "examples/example_snapshot_testing.md",
        "Snapshot testing",
        "",
    ),
    (
        "06_parallel",
        "Parallel workers",
        "Run test files across workers; same-file tests stay on one worker.",
        "examples/example_parallel_workers.md",
        "Parallel execution",
        "",
    ),
    (
        "07_watch",
        "Watch mode",
        "Rerun on file changes during local development.",
        "examples/example_watch_mode.md",
        "Watch mode",
        "",
    ),
    (
        "08_markers",
        "Markers, skip, and retries",
        "Timeouts, retries, skip reasons, and tags for CI filtering.",
        "examples/example_markers_skip.md",
        "Markers / skip",
        "",
    ),
    (
        "09_report_junit",
        "JUnit XML report",
        "Emit XML for GitHub, Jenkins, or GitLab job summaries.",
        "examples/mcp_test_report_junit.yaml",
        "Sample `mcp-test.yaml`",
        "Run with `mcp-test --config examples/mcp_test_report_junit.yaml` after pointing `server.command` at your server.\n",
    ),
    (
        "10_report_json",
        "JSON report",
        "Machine-readable results for custom dashboards and tooling.",
        "examples/mcp_test_report_json.yaml",
        "Sample `mcp-test.yaml`",
        "",
    ),
    (
        "11_report_html",
        "HTML report (human dashboard)",
        "A self-contained HTML file with pass/fail mix and quality-style summary; ideal for local review or CI artifacts.",
        "examples/mcp_test_report_html.yaml",
        "Sample `mcp-test.yaml`",
        "__SAMPLE_REPORT__",
    ),
    (
        "12_plugins",
        "Plugins (assertions, fixtures, reporters)",
        "Load custom behavior through `mcp-test.yaml` and small Python modules.",
        "examples/reference_plugin.py",
        "Reference plugin",
        "",
    ),
    (
        "13_transport_stdio",
        "Stdio transport",
        "The default: launch a subprocess and talk MCP over stdio.",
        "examples/sample_mcp_test.yaml",
        "Full sample config",
        "",
    ),
    (
        "14_transport_sse",
        "SSE transport",
        "Test a remote or local server exposed over Server-Sent Events.",
        "examples/mcp_test_transport_sse.example.yaml",
        "SSE config template",
        "",
    ),
    (
        "15_transport_http",
        "Streamable HTTP",
        "Point tests at an HTTP streamable endpoint.",
        "examples/mcp_test_transport_http.example.yaml",
        "HTTP config template",
        "",
    ),
    (
        "16_github_action",
        "GitHub Action",
        "Wire `mcp-test` in Actions with a one-line or composite pattern.",
        "examples/example_github_actions.md",
        "GitHub Action",
        "",
    ),
    (
        "17_docker",
        "Docker and OCI images",
        "Reproducible `mcp-test` in containers; GHCR tags on `v*`.",
        "examples/example_docker.md",
        "Docker",
        "",
    ),
    (
        "18_pyinstaller",
        "Standalone binary (PyInstaller)",
        "Ship a single executable for environments without Python.",
        "examples/example_pyinstaller.md",
        "PyInstaller",
        "",
    ),
    (
        "19_mcp_init",
        "`mcp-test init` scaffold",
        "Generate a starter test file and `mcp-test.yaml` in one step.",
        "examples/example_mcp_test_init.md",
        "Init",
        "",
    ),
    (
        "20_cli_filters",
        "CLI: `--list`, `-k`, `-m`",
        "Discover and filter by name and marker from the command line.",
        "examples/example_cli_list_filters.md",
        "List / filters",
        "",
    ),
    (
        "21_config_validation",
        "Validate `mcp-test.yaml` without running tests",
        "Fail fast on bad configuration in CI with a small script.",
        "examples/validate_mcp_test_config.py",
        "Validator",
        "Run: `python examples/validate_mcp_test_config.py path/to/mcp-test.yaml`.\n",
    ),
    (
        "22_version_gate",
        "Version gate (MCP-Bastion / mcplint)",
        "Enforce a minimum `mcp-bastion-python` and harness line in preflight CI.",
        "examples/version_gate.py",
        "version_gate",
        "Requires: `pip install mcp-test-harness[mcplint]` when checking Bastion.\n",
    ),
    (
        "23_basic_usage",
        "Imports and public API (Python)",
        "Smoke-check the package from a script: versions and assertion list.",
        "examples/basic_usage.py",
        "basic_usage",
        "Run: `python examples/basic_usage.py`.\n",
    ),
    (
        "24_assert_latency",
        "Latency and performance assertions",
        "Use `assert_latency` (single, mean, p95) with warmups; see the perf doc.",
        "docs/PERFORMANCE.md",
        "PERFORMANCE.md",
        "Also: `docs/TUTORIAL.md` and `examples/patterns_mcp_test.md` for `-m perf` ideas.\n",
    ),
    (
        "25_assert_capabilities",
        "`assert_capabilities`",
        "Verify the server advertises the MCP capabilities you require.",
        "examples/example_mcp_assertions.md",
        "Assertion table",
        "The async demo file exercises multiple helpers, including capabilities patterns.\n",
    ),
    (
        "26_assert_resource",
        "Resources and `assert_resource_read`",
        "Validate `resources/list` and content reads in automated tests.",
        "examples/example_mcp_assertions.md",
        "Resource assertions",
        "",
    ),
    (
        "27_assert_prompt",
        "Prompts and `assert_prompt`",
        "Where your server supports prompts, assert prompt lists and get flows.",
        "examples/example_mcp_assertions.md",
        "Prompt assertions",
        "",
    ),
    (
        "28_assert_tool_schema",
        "`assert_tool_schema`",
        "Lock input schemas for tools to prevent accidental breaking changes.",
        "examples/example_mcp_assertions.md",
        "Tool schema",
        "",
    ),
    (
        "29_assert_protocol_version",
        "`assert_protocol_version`",
        "Pin expected MCP protocol versions after upgrades.",
        "examples/example_mcp_assertions.md",
        "Protocol",
        "",
    ),
    (
        "30_assert_idempotent",
        "Idempotency and `assert_tool_idempotent`",
        "Detect duplicate side effects on safe replay where applicable.",
        "examples/example_mcp_assertions.md",
        "Idempotent tool",
        "",
    ),
]


def _repo_relpath(scenarios_dir: Path, repo_path: str) -> str:
    """Path from scenarios_dir to a repo-root-relative file."""
    root = scenarios_dir.parents[2]
    target = (root / repo_path).resolve()
    return os.path.relpath(target, start=scenarios_dir.resolve()).replace("\\", "/")


def _reports_file_relpath(scenarios_dir: Path, name: str) -> str:
    r = (scenarios_dir.parent / "reports" / name).resolve()
    return os.path.relpath(r, start=scenarios_dir.resolve()).replace("\\", "/")


def _write_one(scenarios_dir: Path, n: int, data: tuple[str, str, str, str, str, str]) -> None:
    slug, title, goal, see_file, see_label, extra = data
    num = f"{n:02d}"
    rest = slug.split("_", 1)[1] if slug.split("_", 1)[0].isdigit() else slug
    path = scenarios_dir / f"scenario_{num}_{rest}.md"

    see_href = _repo_relpath(scenarios_dir, see_file)
    if extra == "__SAMPLE_REPORT__":
        h = _reports_file_relpath(scenarios_dir, "sample_mcp_test_report.html")
        r = _reports_file_relpath(scenarios_dir, "README.md")
        extra = f"Open a built sample: [`{h}`]({h}) (see [`{r}`]({r})).\n\n"
    # Fix assertion doc pointer for 02
    if n == 2:
        mpath = _repo_relpath(scenarios_dir, "examples/example_mcp_assertions.md")
        extra = f"See the mapping in [`example_mcp_assertions.md`]({mpath}).\n\n"

    body = f"""# Scenario {n}: {title}

> **Goal:** {goal}

| Field | |
| --- | --- |
| **Primary example** | [`{see_href}`]({see_href}) — *{see_label}* |
| **Index** | [Scenarios index](README.md) · [Feature demo](../README.md) · [Examples](../../README.md) · [FEATURES_INDEX](../../FEATURES_INDEX.md) |

{extra}
## Try it

1. Install the harness: `pip install mcp-test-harness` (or `pip install -e \".[dev]\"` from a clone).
2. Point any sample `mcp-test.yaml` at your real `server.command` (or a stub) and run from the repo root, e.g. `mcp-test --config <file>` (see the linked file for the exact case).

## See also

- [Feature demo — overview, sample report](../README.md)
- [Examples folder](../../README.md)
- [Developer guide](../../../docs/DEVELOPER_GUIDE.md)
"""
    path.write_text(textwrap.dedent(body).lstrip(), encoding="utf-8")
    root = scenarios_dir.parents[2]
    print(path.relative_to(root))


def main() -> None:
    scenarios_dir = Path(__file__).resolve().parent
    if len(SCENARIOS) != 30:
        raise SystemExit(f"expected 30 scenarios, got {len(SCENARIOS)}")
    for i, s in enumerate(SCENARIOS, start=1):
        _write_one(scenarios_dir, i, s)


if __name__ == "__main__":
    main()
