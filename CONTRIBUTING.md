# Contributing

Thanks for helping improve **MCP Test Harness**.

## Where things live

| What | Where |
|------|--------|
| **User + maintainer docs** | [docs/README.md](docs/README.md) (hub) |
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
python -m pytest tests/ -q --cov=src/mcp_test_harness --cov-fail-under=100
```

The project targets **100%** line coverage on `src/mcp_test_harness` (see [pyproject.toml](pyproject.toml) `[tool.coverage.*]`; `stdio_mcp.py` is listed under `omit` for the fail-under gate).

## Releases

- Bump **`version`** in [pyproject.toml](pyproject.toml) and in [server.json](server.json) (and [CITATION.cff](CITATION.cff) if you track version there).
- Add a new section to [CHANGELOG.md](CHANGELOG.md) with the new tag date and a concise **Added** / **Fixed** / **Changed** list.
- GitHub: tag the commit (e.g. `v1.0.0`) and publish the wheel/sdist to PyPI per your project’s release workflow.
