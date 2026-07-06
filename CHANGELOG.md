# Changelog

All notable changes to this project are documented in this file. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.0.1] - 2026-07-06

### Fixed

- **CallToolResult.isError:** assertions now read `isError` on the MCP result object (per spec and FastMCP), not only on content items. Fixes false passes in `assert_tool_call`, false failures in `assert_tool_rejects` / `assert_tool_denied`, and `assert_degrades_gracefully` misfires against spec-compliant servers.

## [2.0.0] - 2026-07-06

### Changed

- **Major release (semver 2.0.0):** bundles v1.2 platform QA (coverage map, unified portal, SARIF, security payloads, baselines) and v1.3 diagnostics (MCP trace, chaos, `mcp-test generate`), e2e dogfood, and 100% coverage CI gate.
- **All 18 PyPI artifacts** aligned at **2.0.0**: `mcp-test-harness` plus 17 optional `mcp-test-harness-*` provider packs under `packages/`.
- **Docker / GHCR** images tagged **`2.0.0`**, **`2.0.0-dev`**, **`latest`**, and **`dev`** on `v2.0.0` git tag.
- **`SessionResults.harness_version`** now tracks `mcp_test_harness.__version__` (no hardcoded scheduler string).

### Added

- **Bulk optional-package publish** on `v*` tags via [`.github/workflows/publish.yml`](.github/workflows/publish.yml) matrix job.

## [1.3.0] - 2026-07-05

### Added

- **MCP trace capture:** per-test JSON-RPC event log (`mcp_trace`) with stdio pollution hints; interactive timeline in HTML reports.
- **Protocol-aware chaos:** `@marker(tags=["chaos"], chaos_faults=[...])` — delay, 503, truncate, schema drift on `call_tool`.
- **`mcp-test generate`:** offline schema-driven test scaffolding from live `tools/list` (+ optional `--drift-report`).
- **E2E dogfood:** `tests/test_harness_dogfood_e2e.py` runs the real `mcp-test` CLI against bundled FastMCP fixtures; CI enforces `coverage report --fail-under=100` on every PR and uploads coverage HTML + dogfood smoke report on `main`.
- **Docs/images:** [`docs/images/dogfood-e2e.svg`](docs/images/dogfood-e2e.svg); README and [DEVELOPER.md](docs/DEVELOPER.md) dogfood sections.
- **Developer examples (v1.3):** [example_mcp_trace.md](examples/example_mcp_trace.md), [example_chaos_testing.md](examples/example_chaos_testing.md), [example_generate_scaffold.md](examples/example_generate_scaffold.md), [platform-qa demo pack](examples/feature-demo/platform-qa/README.md).

### Fixed

- **GitHub Pages:** deploy only `html/` (with `.nojekyll`) instead of the entire repository; fixes failed `pages-build-deployment` runs.

## [1.2.0] - 2026-07-05

### Added

- **Platform QA (v1.2):** `coverage.py`, `security_payloads.py`, `resiliency.py`, `baselines.py`, `unified_report.py` — coverage map, security payload packs, resiliency assertions, baseline perf gates, unified portal in JSON/HTML.
- **`assert_throughput` SLO params:** `max_p99_ms` and `max_error_rate` alongside `min_rps`.
- **SARIF export:** `--report-format sarif` or `--sarif-output` for GitHub Code Scanning; OWASP MCP rule metadata on security findings (`security_rules.py`).
- **PR summary:** `--pr-summary-output` markdown; GitHub Action `pr-comment` input posts/updates PR comments.
- **Docs:** [POSITIONING.md](docs/POSITIONING.md), updated [COMPARISON.md](docs/COMPARISON.md), [SECURITY_TESTING.md](docs/SECURITY_TESTING.md), README visuals.

## [1.1.0] - 2026-04-25

### Added

- **`assert_throughput`:** concurrent `call_tool` load-style checks with optional minimum **RPS** budget (complements `assert_latency`).
- **CLI:** `--fail-fast` (stop after first failure, error, or timeout), `--last-failed` (re-run from `.mcp_test_harness/last-failed.json`); stricter list/config handling as documented in [RELEASING](docs/RELEASING.md).
- **Scheduler:** **LPT (greedy) assignment** of whole test modules to parallel workers; shared fail-stop for parallel `--fail-fast`.
- **Config:** validate `mcp-test.yaml` / `mcp-test.toml` before `HarnessConfig` load (clear aggregated errors, exit 2 on failure).
- [`.github/workflows/docker-publish.yml`](.github/workflows/docker-publish.yml) — on **`v*`** tags, build and push **runtime** and **dev** images to **GHCR** (`ghcr.io/vaquarkhan/mcp-test-harness`). [docs/RELEASING.md](docs/RELEASING.md) documents PyPI + Docker release steps with GitHub settings.
- [docs/LLM_TEST_GENERATION.md](docs/LLM_TEST_GENERATION.md) — guidance on **LLM-assisted** test drafting vs **automatic** “connected LLM” generation in CI; linked from [COMPARISON](docs/COMPARISON.md) and the [docs hub](docs/README.md).
- **Docs:** [DEVELOPER.md](docs/DEVELOPER.md#stdio_mcp-and-the-coverage-gate) — **stdio_mcp.py** and the **100%** `coverage` fail-under: intentional `omit` (maintainer policy), **integration** coverage, and production-grade quality for the **rest** of `mcp_test_harness` under the gate.
- An expanded [examples](examples/README.md) set: [assertions_async_demo.py](examples/assertions_async_demo.py), [validate_mcp_test_config.py](examples/validate_mcp_test_config.py), [sample_mcp_test.yaml](examples/sample_mcp_test.yaml), [patterns_mcp_test.md](examples/patterns_mcp_test.md). Cross-links from the [docs hub](docs/README.md), [README](README.md), and [DEVELOPER_GUIDE](docs/DEVELOPER_GUIDE.md).
- [docs/COLLECTIONS.md](docs/COLLECTIONS.md) — **Postman / Newman–style** multi-step flows, environments, and how to express them in **Python** today; **roadmap** for optional declarative collections; linked from [COMPARISON](docs/COMPARISON.md) and the [docs hub](docs/README.md).
- [examples/FEATURES_INDEX.md](examples/FEATURES_INDEX.md) and **per-feature** `example_*.md` / `mcp_test_*.yaml` in [examples](examples/) so every README *core* feature has a **dedicated** sample; [examples/README.md](examples/README.md) expanded.

## [1.0.0] - 2026-04-24

### Changed

- **PyPI / semver:** `Development Status` trove classifier is now **`5 - Production/Stable`** (no longer Beta). Version **1.0.0** marks this stable line for dependency ranges and public API expectations.

## [0.1.2] - 2026-04-24

### Added

- **Docs:** [docs/DOCKER.md](docs/DOCKER.md) (PyPI, GitHub Packages / `ghcr.io` discovery, Mermaid for image targets), [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) (Mermaid flow + sequence), [docs/EDITORS.md](docs/EDITORS.md) (Visual Studio Code and Cursor: snippets, Mermaid, extensions). Cross-links in [README](README.md), [docs hub](docs/README.md), [docs/index.md](docs/index.md), [docs/DISCOVERY.md](docs/DISCOVERY.md), and [CONTRIBUTING](CONTRIBUTING.md). **[project.urls](https://github.com/vaquarkhan/mcp-test-harness/blob/main/pyproject.toml):** `Docker`, `Architecture`, `Editors` for PyPI project links.

### Fixed

- **Schema / resources:** `list_resources` shape validation coerces Pydantic `AnyUrl` and similar types via `str(uri)`; rejects `bool` and numeric `uri` values that are not real URIs.
- **Assertions:** `assert_capabilities` falls back to `_mcp_harness_init_result` (object or dict) when the MCP client session does not expose `server_capabilities` / `capabilities` directly.
- **Caching:** `list_tools` results are cached in a `WeakKeyDictionary` (with a guarded `__dict__` path for mocks); handles slotted sessions with and without a `__weakref__` slot.
- **Scaffold (`mcp-test init`):** generated tests use the harness `@skip` decorator instead of `pytest.skip`; template is **harness-oriented** (no `pytest` import in the starter file).
- **Post-connect validation:** `list_resources` / `list_prompts` checks use direct `await` calls (clearer than lambdas in a loop).
- **CLI / tests:** `Path.stat` test mock accepts `*args, **kwargs` for **Python 3.13+** (`follow_symlinks`); watch-mode debounce paths covered by tests using `MCP_TEST_HARNESS_WATCH_MAX_OUTER` and short poll intervals.
- **Integration:** minimal **FastMCP** subprocess test exercises `stdio_client_exposing_process` (real process).

### Changed

- **PyPI classifiers:** `Development Status :: 4 - Beta`; added `Programming Language :: Python :: 3.13`.
- **Coverage:** 100% line coverage on `src/mcp_test_harness` (with `stdio_mcp.py` omitted from the fail-under set as vendored I/O; still exercised at runtime and via integration test).

## [0.1.1] - 2026-04-24

### Added

- [docs/DISCOVERY.md](docs/DISCOVERY.md) (registry / promotion checklist), [docs/index.md](docs/index.md) (docs landing), [server.json](server.json) (tooling metadata for registries).
- **Config:** `validate_schema_each_parallel_worker`, `schema_probe_call_tool`; parallel workers optionally skip duplicate post-connect schema work (worker 0 only by default).
- **Watch mode:** `MCP_TEST_HARNESS_WATCH_INTERVAL`, `MCP_TEST_HARNESS_WATCH_DEBOUNCE` (debounced file-change detection).
- **Optional `mcplint`:** `mcp-bastion-python` moved to optional extra `[mcplint]`; core install stays lightweight.

### Fixed

- Session lifecycle: `__aexit__` on initialize failure; content-shape probe in post-connect validation; `list_tools` caching for repeated assertions; `Path.stat` and resource URI tests.

## [0.1.0] - 2024-01-15

### Added

- Initial PyPI release of **MCP Test Harness**: `mcp-test` CLI, discovery, stdio/SSE/HTTP transports, fixtures, parallel runs, JUnit/JSON/HTML reports, plugin hooks, and MCP assertion library.

**GitHub releases (tags and assets):** [github.com/vaquarkhan/mcp-test-harness/releases](https://github.com/vaquarkhan/mcp-test-harness/releases)
