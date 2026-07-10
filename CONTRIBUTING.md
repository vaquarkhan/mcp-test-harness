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

## How to contribute

1. **Issues** — bug reports and feature ideas: open a [GitHub Issue](https://github.com/vaquarkhan/mcp-test-harness/issues) with a minimal repro for bugs.
2. **Pull requests** — keep changes focused; match existing style; run the test suite and coverage (see below).
3. **Documentation** — fixes and new guides are welcome; link new pages from [docs/README.md](docs/README.md) and, when relevant, the root [README.md](README.md).

## Develop & test

```bash
pip install -e ".[dev]"
set PYTHONPATH=src   # Windows; on POSIX: export PYTHONPATH=src
coverage run -m pytest tests/ --ignore=tests/test_workspace.py -q
coverage report --fail-under=100
```

The project enforces **100%** line coverage on `src/mcp_test_harness` (see [pyproject.toml](pyproject.toml) `[tool.coverage.*]`). **E2E dogfood** tests in [`tests/test_harness_dogfood_e2e.py`](tests/test_harness_dogfood_e2e.py) run the real `mcp-test` CLI against [`tests/fixtures/minimal_mcp_server.py`](tests/fixtures/minimal_mcp_server.py) — a test harness should prove itself in CI, not only with mocks. See [docs/DEVELOPER.md#end-to-end-dogfood](docs/DEVELOPER.md#end-to-end-dogfood).

**Browser note:** a few lines in `pdf_export.py` / HTML screenshot helpers only execute when headless Chrome or Edge is installed. GitHub Actions runners include a browser; a local `coverage report --fail-under=100` may show ~99% without one. Install Chrome/Edge, or run the same suite CI uses, before treating a local miss as a regression.

## Releases

See **[docs/RELEASING.md](docs/RELEASING.md)** for the full **PyPI + GHCR** checklist (trusted publishing, Actions permissions, `docker pull`).

- Bump **`version`** in [pyproject.toml](pyproject.toml) and in [server.json](server.json) (and [CITATION.cff](CITATION.cff) if you track version there).
- Add a new section to [CHANGELOG.md](CHANGELOG.md) with the new tag date and a concise **Added** / **Fixed** / **Changed** list.
- Push a **`vX.Y.Z`** tag on the release commit: [`.github/workflows/publish.yml`](.github/workflows/publish.yml) uploads to **PyPI**; [`.github/workflows/docker-publish.yml`](.github/workflows/docker-publish.yml) pushes **runtime** and **dev** images to **GHCR**.
