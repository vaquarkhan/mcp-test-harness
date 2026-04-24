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
python -m pytest tests/ -q --cov=src/mcp_test_harness --cov-fail-under=100
```

The coverage fail-under (see [pyproject.toml](../pyproject.toml) `[tool.coverage.*]`) applies to the **core harness** package. Vendored I/O in `stdio_mcp.py` is listed under `omit` for the gate but is still exercised in integration tests.

## stdio_mcp and the coverage gate

- **`fail_under = 100`** (line coverage) applies to `src/mcp_test_harness` **except** [`stdio_mcp.py`](../src/mcp_test_harness/stdio_mcp.py), which is **listed under `omit`** in `[tool.coverage.*]`.
- **Why:** that module is **subprocess and stdio I/O**-heavy. Hitting every branch in CI would require elaborate synthetic mocks; maintainers **chose** to keep the 100% bar on the rest of the framework while still **running** `stdio_mcp` through **integration** tests (e.g. `test_stdio_mcp*`) and real stdio use.
- This is a **documented, intentional** trade-off. It is **not** a bug, and it does not mean the project is "half production-ready"—only that the **line gate** is scoped to a consistent subset. Everything else in `mcp_test_harness` (under the current `omit` list) is expected to pass the gate for production-grade releases.

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
