# Changelog

All notable changes to this project are documented in this file. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
