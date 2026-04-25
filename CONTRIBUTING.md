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
| **Maintainer delivery plan** (not a public product commitment) | [Maintainer delivery plan](#maintainer-delivery-plan) (below) |

## Maintainer delivery plan

This section replaces a standalone roadmap file. **It is for contributors and maintainers** — priorities shift with feedback and capacity; it is **not** a customer-facing release contract.

Phases preserve core identity: **MCP-aware**, **CI-first**, **deterministic by default**.

### Now (high ROI, low risk)

1. `mcp-test doctor` onboarding and health diagnostics (**implemented**).
2. HTML report UX polish (grouping, filter, sort, status badges, run metadata).
3. Performance strategy docs and explicit product positioning.
4. Example/demo expansion for feature coverage and discoverability.

### Next (major value unlock)

1. Security baseline assertions: prompt-injection payload checks, traversal/injection payload checks, secret leak scanner.
2. MCP trace capture per test and timeline rendering in HTML.
3. Tool/resource coverage map (“advertised but not tested”).
4. Throughput + baseline-based performance regression gates.

### Later (platform and enterprise)

1. Contract recording/replay and compatibility matrix runs.
2. GitHub Checks / reporter ecosystem integrations.
3. Governance features: signed audit exports, role/tenant matrices, policy-as-code plugin adapters.

### Scope guardrails

**Core harness should own:** protocol-aware assertions and CI gates; reproducible local/CI reports.

**Core harness should not replace:** distributed load generators; full observability backends; org-specific policy engines (those stay integrations/plugins).

### Candidates not yet scheduled (backlog)

- **MCP Inspector workflow:** optional CLI or docs-only path so the same `server-command` / transport as `mcp-test` can drive [MCP Inspector](https://github.com/modelcontextprotocol/inspector) for manual exploration (complements CI, does not duplicate the Inspector UI).
- **Composition / multi-protocol scenarios:** targeted **tests and docs** for bridge-style setups where MCP sits beside other agent surfaces; empirical CI checks — **not** a promise of full formal verification (TLA+/theorem-proving) for arbitrary servers; any formal-methods work stays **narrow, optional, and clearly scoped** if explored.

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

The project targets **100%** line coverage on `src/mcp_test_harness` (see [pyproject.toml](pyproject.toml) `[tool.coverage.*]`). **[`stdio_mcp.py`](src/mcp_test_harness/stdio_mcp.py) is excluded from that gate** on purpose: vendored I/O and error branches are covered by **integration** tests and runtime use, not a second layer of line-by-line synthetic mocks. See [docs/DEVELOPER.md#stdio_mcp-and-the-coverage-gate](docs/DEVELOPER.md#stdio_mcp-and-the-coverage-gate) for the rationale.

## Releases

See **[docs/RELEASING.md](docs/RELEASING.md)** for the full **PyPI + GHCR** checklist (trusted publishing, Actions permissions, `docker pull`).

- Bump **`version`** in [pyproject.toml](pyproject.toml) and in [server.json](server.json) (and [CITATION.cff](CITATION.cff) if you track version there).
- Add a new section to [CHANGELOG.md](CHANGELOG.md) with the new tag date and a concise **Added** / **Fixed** / **Changed** list.
- Push a **`vX.Y.Z`** tag on the release commit: [`.github/workflows/publish.yml`](.github/workflows/publish.yml) uploads to **PyPI**; [`.github/workflows/docker-publish.yml`](.github/workflows/docker-publish.yml) pushes **runtime** and **dev** images to **GHCR**.
