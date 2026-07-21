# Developer handbook (this repository)

This page is for **people working in the mcp-test-harness repo** (patches, releases, and deeper internals). For **using** the harness in *your* MCP server project, use the [Developer Guide](DEVELOPER_GUIDE.md) and the [examples/](../examples/README.md) catalog.

| Topic | Where |
|--------|--------|
| **Install, CI, and coverage gate** | [CONTRIBUTING.md](../CONTRIBUTING.md) |
| **User-facing config, CLI, and assertions (full reference)** | [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) |
| **Example scripts by feature** | [examples/README.md](../examples/README.md) · [FEATURES_INDEX.md](../examples/FEATURES_INDEX.md) (one example per “core” feature) |
| **Documentation hub (adoption order)** | [README.md](README.md) in this `docs/` folder |
| **Mermaid architecture** | [ARCHITECTURE.md](ARCHITECTURE.md) |
| **CI reports and JUnit in Actions** | [CI_AND_REPORTS.md](CI_AND_REPORTS.md) |
| **Postman-style collections, chained steps, environments (doc)** | [COLLECTIONS.md](COLLECTIONS.md) |
| **Latency and `mcp-test -m perf`** | [PERFORMANCE.md](PERFORMANCE.md) |
| **Stateless SEP-2575 suite** | [TUTORIAL_STATELESS.md](TUTORIAL_STATELESS.md) · [design/RFC-006-stateless-mcp.md](design/RFC-006-stateless-mcp.md) · `src/mcp_test_harness/stateless/` |
| **Editor / snippets** | [EDITORS.md](EDITORS.md) |
| **Docker and OCI** | [DOCKER.md](DOCKER.md) |
| **Feature traceability (for maintainers)** | [IMPLEMENTATION_CHECKLIST.md](IMPLEMENTATION_CHECKLIST.md) |
| **Changelog and semver** | [CHANGELOG.md](../CHANGELOG.md) |
| **PyPI + GHCR release (tag `v*`)** | [RELEASING.md](RELEASING.md) |

## Clone and run the test suite

```bash
git clone https://github.com/vaquarkhan/mcp-test-harness.git
cd mcp-test-harness
pip install -e ".[dev]"
# Windows: set PYTHONPATH=src
# macOS / Linux: export PYTHONPATH=src
coverage run -m pytest tests/ --ignore=tests/test_workspace.py -q
coverage report --fail-under=100
```

The coverage fail-under (see [pyproject.toml](../pyproject.toml) `[tool.coverage.*]`) applies to the **core harness** package at **100%** line coverage, including subprocess I/O paths exercised by integration and dogfood tests.

## End-to-end dogfood

The harness validates itself with real CLI subprocess runs — not only mocks:

| Path | Role |
|------|------|
| [`tests/fixtures/minimal_mcp_server.py`](../tests/fixtures/minimal_mcp_server.py) | FastMCP echo server (stdio) |
| [`tests/fixtures/harness_self_test/`](../tests/fixtures/harness_self_test/) | Harness-style tests consumed by `mcp-test` |
| [`tests/test_harness_dogfood_e2e.py`](../tests/test_harness_dogfood_e2e.py) | pytest e2e: CLI → server → JSON/HTML reports + `doctor` |
| [`tests/fixtures/rich_mcp_server.py`](../tests/fixtures/rich_mcp_server.py) | Multi-tool + resource/prompt/error fixture for seam tests |
| [`tests/fixtures/harness_seam_test/`](../tests/fixtures/harness_seam_test/) | README contracts + coverage-exercising cases for `mcp-test` |
| [`tests/test_seam_e2e.py`](../tests/test_seam_e2e.py) | Seam e2e: record round-trip, capabilities contract, coverage>0, init→run, cp1252 help |

`tests/fixtures/harness_self_test/` and `harness_seam_test/` are **ignored by pytest** (`addopts` in pyproject) so only `mcp-test` discovers those cases. Run dogfood / seams:

```bash
python -m pytest tests/test_harness_dogfood_e2e.py tests/test_seam_e2e.py -m e2e -v
```

**Why seams matter:** 100% line coverage proves lines ran; bugs like invalid `record` codegen, `assert_capabilities` doc drift, and empty coverage maps live at component boundaries. See [CONTRIBUTING.md](../CONTRIBUTING.md).

## stdio_mcp and the coverage gate

- **`fail_under = 100`** (line coverage) applies to all of `src/mcp_test_harness`, including [`stdio_mcp.py`](../src/mcp_test_harness/stdio_mcp.py).
- Subprocess/stdio branches are covered via **integration tests** (`test_stdio_mcp*`), **transport** tests, and **e2e dogfood** — the same paths production `mcp-test` uses.

## Package layout (short map)

- **`src/mcp_test_harness/`** — **CLI, config, discovery, fixtures, transport, lifecycle, scheduler, executor, plugins, schema, reporting, snapshots, assertion helpers.**
- **`src/mcplint/`** — optional shim that pins and exposes [MCP-Bastion](https://github.com/vaquarkhan/MCP-Bastion) for lint-style checks; not required to run the harness.
- **`packages/mcp-test-harness-*`** — small optional add-ons (provider-specific helpers); their versions track the main [pyproject.toml](../pyproject.toml) release.
- **`tests/`** — unit and integration tests; the offline check `tests/test_pyproject.py` runs in the quick CI job without heavy optional deps.
- **`.github/workflows/`** — `validate.yml` (quick on PRs, full on `main` + manual).

## When you change the public surface

- Bump **`version`** in [pyproject.toml](../pyproject.toml), [server.json](../server.json), and, if you use it, [CITATION.cff](../CITATION.cff).
- Add a section to [CHANGELOG.md](../CHANGELOG.md) and, if the example catalog changes, update [examples/README.md](../examples/README.md).

## Examples you can run

From the repo root after `pip install -e ".[dev]"`:

| Script / file | Intent |
|---------------|--------|
| [examples/basic_usage.py](../examples/basic_usage.py) | `python examples/basic_usage.py` — check imports and print assertion names |
| [examples/version_gate.py](../examples/version_gate.py) | Enforce minimum installed versions in CI or scripts |
| [examples/reference_plugin.py](../examples/reference_plugin.py) | Custom assertion, fixture, and reporter in a **plugin** |
| [examples/assertions_async_demo.py](../examples/assertions_async_demo.py) | **Duck-typed** session: most `assert_*` helpers in one process |
| [examples/validate_mcp_test_config.py](../examples/validate_mcp_test_config.py) | Validate a YAML/TOML file with `validate_config_file()` |
| [../examples/patterns_mcp_test.md](../examples/patterns_mcp_test.md) | **Copy-paste** `mcp-test.yaml`, markers, and test skeletons |

**Note:** the harness’s default test directory is `tests/`. The patterns doc is for copying into *your* project, not for discovery inside this repository.
