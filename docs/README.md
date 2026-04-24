# MCP Test Harness — documentation hub

This repository uses the same documentation **style** as [MCP-Bastion](https://github.com/vaquarkhan/MCP-Bastion): a central **hub** (this file), **adoption paths** (read in order), and deep-dive guides linked from one table.

**Community:** open a GitHub **Issue** for bugs or feature requests, a **Discussion** (if enabled) for integration questions, or a **PR** for docs and examples.

**Companion project (runtime security):** [MCP-Bastion](https://github.com/vaquarkhan/MCP-Bastion) — prompt injection defense, PII redaction, rate limits, RBAC. MCP Test Harness focuses on **automated test execution**; Bastion on **operational protection**.

---

## Adoption paths (read in order)

| Goal | Read in order |
|------|----------------|
| **Fastest first run** (install, scaffold, one command) | [QUICK_START.md](QUICK_START.md) |
| **Step-by-step tutorial** | [TUTORIAL.md](TUTORIAL.md) |
| **Everything else** (config, assertions, parallel, reports, plugins) | [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) |
| **CI, JUnit, JSON, HTML — do I need to “publish” reports?** | [CI_AND_REPORTS.md](CI_AND_REPORTS.md) |
| **Performance / latency** (same tests as functional; `assert_latency`, `-m perf`) | [PERFORMANCE.md](PERFORMANCE.md) |
| **Ecosystem** (Conformance, mcp-eval, MCPMark, testmcpy — vs this harness) | [COMPARISON.md](COMPARISON.md) |
| **Registries, PyPI, release promotion** (checklist — same style as [MCP-Bastion](https://github.com/vaquarkhan/MCP-Bastion)) | [DISCOVERY.md](DISCOVERY.md) |
| **Docker / OCI** (images, `ghcr.io` / **GitHub Packages** discovery, Mermaid) | [DOCKER.md](DOCKER.md) |
| **Visual architecture** (Mermaid: CLI → session → test) | [ARCHITECTURE.md](ARCHITECTURE.md) |
| **Visual Studio Code, Cursor, snippets** (editor workflow + Mermaid in preview) | [EDITORS.md](EDITORS.md) |
| **Why the harness looks like this** (architecture / trade-offs) | [DECISIONS.md](DECISIONS.md) |
| **Gap / implementation checklist** (for maintainers) | [IMPLEMENTATION_CHECKLIST.md](IMPLEMENTATION_CHECKLIST.md) |
| **Releases, upgrades, what changed** | [CHANGELOG.md](../CHANGELOG.md) |
| **How to contribute** (tests, PRs, release checklist) | [CONTRIBUTING.md](../CONTRIBUTING.md) |

---

## All documents

| Document | What it is |
|----------|------------|
| [QUICK_START.md](QUICK_START.md) | **Time-to-value:** install, `mcp-test init`, run tests |
| [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) | **Canonical reference** — config, stdio/SSE/HTTP, assertions, fixtures, schema, reporting, plugins |
| [TUTORIAL.md](TUTORIAL.md) | Longer **walkthrough** for new users |
| [CI_AND_REPORTS.md](CI_AND_REPORTS.md) | **CI and reports:** exit codes, JUnit for Actions, when to upload/publish HTML |
| [PERFORMANCE.md](PERFORMANCE.md) | **Performance tests:** `assert_latency` (p95, warmup), `marker(tags=[…])` + `mcp-test -m perf` |
| [COMPARISON.md](COMPARISON.md) | **Ecosystem map:** other MCP tools (conformance, evals, benchmarks) and how they fit with Harness + Bastion |
| [DISCOVERY.md](DISCOVERY.md) | **Discovery / registries:** internal checklist for releases (PyPI, awesome lists, `server.json`, related tooling) |
| [DOCKER.md](DOCKER.md) | **Container images** — build targets, [PyPI](https://pypi.org/project/mcp-test-harness/) vs **local build**, [GitHub Packages](https://github.com/vaquarkhan?tab=packages) & future **GHCR** |
| [ARCHITECTURE.md](ARCHITECTURE.md) | **Mermaid** high-level and sequence diagrams (how a test run works) |
| [EDITORS.md](EDITORS.md) | **VS Code / Cursor** — `.vscode` snippets, extensions, Mermaid preview |
| [index.md](index.md) | **Short docs landing** (for GitHub Pages or static site generators) — links into this hub |
| [Dockerfile](../Dockerfile) (repo root) | **OCI image** for `mcp-test` — build/run notes in root [README.md](../README.md#docker) |
| [../server.json](../server.json) (repo root) | **MCP registry / tooling** metadata; bump `version` with [pyproject.toml](../pyproject.toml) on release |
| [CITATION.cff](../CITATION.cff) (repo root) | **Optional citation** — metadata; [LICENSE](../LICENSE) is MIT |
| [DECISIONS.md](DECISIONS.md) | Product and architecture **decision log** |
| [IMPLEMENTATION_CHECKLIST.md](IMPLEMENTATION_CHECKLIST.md) | **Maintainer** checklist for features vs. source locations |
| [CHANGELOG.md](../CHANGELOG.md) | **Version history** (Keep a Changelog; for PyPI / release notes) |
| [CONTRIBUTING.md](../CONTRIBUTING.md) | **Contributing** — dev setup, `pytest` + coverage, release checklist |

**Editor quality-of-life (this repo):** [../.vscode/mcp-test-harness.code-snippets](../.vscode/mcp-test-harness.code-snippets) — VS Code / Cursor snippets (`mcp-assert-tool`, `mcp-test-async`, …).

**Root [README.md](../README.md):** project pitch, feature matrix, **Docker** [Dockerfile](../Dockerfile) / installation, and links back here.

---

## GitHub Pages (optional)

If you enable GitHub Pages for the `docs/` folder, you can set the entry to [index.md](index.md) (short landing with links) or to this [README](README.md) as the main hub, depending on your theme.
