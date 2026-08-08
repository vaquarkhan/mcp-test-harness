# Contributing

Thanks for helping improve **MCP Test Harness**.

## Where things live

| What | Where |
|------|--------|
| **User + maintainer docs** | [docs/README.md](docs/README.md) (hub) |
| **Developer handbook (this repo)** | [docs/DEVELOPER.md](docs/DEVELOPER.md) |
| **Runnable examples by feature** | [examples/README.md](examples/README.md) |
| **Release & upgrade notes** | [CHANGELOG.md](CHANGELOG.md) |
| **Registries, PyPI, promotion** | [docs/DISCOVERY.md](docs/DISCOVERY.md) |
| **Docker & OCI (images, GHCR, PyPI)** | [docs/DOCKER.md](docs/DOCKER.md) |
| **Mermaid architecture diagrams** | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| **Visual Studio Code / Cursor** | [docs/EDITORS.md](docs/EDITORS.md) |
| **Architecture / trade-offs** | [docs/DECISIONS.md](docs/DECISIONS.md) |
| **Optional citation (papers)** | [CITATION.cff](CITATION.cff) |
| **License** | [LICENSE](LICENSE) · [NOTICE](NOTICE) |
| **Sponsors** | [SPONSORS.md](SPONSORS.md) |

## How to contribute

1. **Issues** — bug reports and feature ideas: open a [GitHub Issue](https://github.com/vaquarkhan/mcp-test-harness/issues) with a minimal repro for bugs.
2. **Pull requests** — keep changes focused; match existing style; run the test suite and coverage (see below).
3. **Documentation** — fixes and new guides are welcome; link new pages from [docs/README.md](docs/README.md) and, when relevant, the root [README.md](README.md).

## Develop & test

```bash
pip install -e ".[dev]"
# Optional Bastion/mcplint pairing (heavy ML transitive deps — not needed for core tests):
# pip install -e ".[dev,mcplint]"
set PYTHONPATH=src   # Windows; on POSIX: export PYTHONPATH=src
# Prefer scoping to tests/ (configured as testpaths). examples/ need `mcp-test`, not plain pytest.
coverage run -m pytest -q
coverage report --fail-under=100
```

The project enforces **100%** line coverage on `src/mcp_test_harness` (see [pyproject.toml](pyproject.toml) `[tool.coverage.*]`). Browser/PDF/screenshot paths are covered with **mocked** headless Chrome/Edge in [`tests/test_browser_and_edge_coverage.py`](tests/test_browser_and_edge_coverage.py), so the gate must pass on a clean checkout without a browser installed. **E2E dogfood** tests in [`tests/test_harness_dogfood_e2e.py`](tests/test_harness_dogfood_e2e.py) run the real `mcp-test` CLI against [`tests/fixtures/minimal_mcp_server.py`](tests/fixtures/minimal_mcp_server.py) — a test harness should prove itself in CI, not only with mocks. See [docs/DEVELOPER.md#end-to-end-dogfood](docs/DEVELOPER.md#end-to-end-dogfood).

**Seam / contract e2e (required for correctness):** line coverage proves lines ran; it does not prove boundaries. Prefer tests that:

1. **Execute generated artifacts** — `ast.parse` + run `mcp-test record` / `generate` output against a real server (not substring-only checks).
2. **Match documented contracts** — README/docstring examples against a real FastMCP server (e.g. `assert_capabilities(mcp_server, {"tools": {}})`).
3. **Assert outcomes** — after tool calls, `coverage.tested.tools` is non-empty; init YAML passes `validate_config_file` and runs.
4. **Use a rich fixture** — [`tests/fixtures/rich_mcp_server.py`](tests/fixtures/rich_mcp_server.py) (multiple tools, resource, prompt, error tool) via [`tests/test_seam_e2e.py`](tests/test_seam_e2e.py).

## Releases

See **[docs/RELEASING.md](docs/RELEASING.md)** for the full **PyPI + GHCR** checklist (trusted publishing, Actions permissions, `docker pull`).

- Bump **`version`** in [pyproject.toml](pyproject.toml) and in [server.json](server.json) (and [CITATION.cff](CITATION.cff) if you track version there).
- Add a new section to [CHANGELOG.md](CHANGELOG.md) with the new tag date and a concise **Added** / **Fixed** / **Changed** list.
- Push a **`vX.Y.Z`** tag on the release commit: [`.github/workflows/publish.yml`](.github/workflows/publish.yml) uploads to **PyPI**; [`.github/workflows/docker-publish.yml`](.github/workflows/docker-publish.yml) pushes **runtime** and **dev** images to **GHCR**.
