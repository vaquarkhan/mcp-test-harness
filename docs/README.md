# MCP Test Harness — documentation hub

This repository uses the same documentation **style** as [MCP-Bastion](https://github.com/vaquarkhan/MCP-Bastion): a central **hub** (this file), **adoption paths** (read in order), and deep-dive guides linked from one table.

**Community:** open a GitHub **Issue** for bugs or feature requests, a **Discussion** (if enabled) for integration questions, or a **PR** for docs and examples.

**Companion project (runtime security):** [MCP-Bastion](https://github.com/vaquarkhan/MCP-Bastion) — prompt injection defense, PII redaction, rate limits, RBAC. MCP Test Harness focuses on **automated test execution**; Bastion on **operational protection**.

**Product value proposition:** one MCP-aware tool for **functional**, **regression**, and **performance** testing in CI. Teams can fail a PR on correctness drift *or* latency regressions without splitting work across unrelated frameworks.

---

## Adoption paths (read in order)

| Goal | Read in order |
|------|----------------|
| **Fastest first run** (install, scaffold, one command) | [QUICK_START.md](QUICK_START.md) |
| **See all three testing types in examples** (functional, regression, performance) | [../examples/feature-demo/README.md](../examples/feature-demo/README.md) |
| **Step-by-step tutorial** | [TUTORIAL.md](TUTORIAL.md) |
| **Everything else** (config, assertions, parallel, reports, plugins) | [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) |
| **Repo developer setup, test layout, examples index** | [DEVELOPER.md](DEVELOPER.md) |
| **CI, JUnit, JSON, HTML — do I need to “publish” reports?** | [CI_AND_REPORTS.md](CI_AND_REPORTS.md) |
| **Performance / latency** (same tests as functional; `assert_latency`, `-m perf`) | [PERFORMANCE.md](PERFORMANCE.md) |
| **Performance strategy** (why perf belongs in the harness; scope + roadmap) | [PERFORMANCE_TESTING_STRATEGY.md](PERFORMANCE_TESTING_STRATEGY.md) |
| **Security testing strategy** (prompt injection, payload checks, leak detection) | [SECURITY_TESTING.md](SECURITY_TESTING.md) |
| **Contract + compatibility strategy** (drift protection, version/client matrix) | [CONTRACT_AND_COMPAT.md](CONTRACT_AND_COMPAT.md) |
| **Enterprise governance** (audit/policy/tenant guidance) | [ENTERPRISE_GOVERNANCE.md](ENTERPRISE_GOVERNANCE.md) |
| **Plugin registry** (integration catalog placeholder) | [PLUGIN_REGISTRY.md](PLUGIN_REGISTRY.md) |
| **Ecosystem** (conformance/eval/benchmark categories vs this harness) | [COMPARISON.md](COMPARISON.md) |
| **LLM-assisted test generation** (when it helps vs when to avoid) | [LLM_TEST_GENERATION.md](LLM_TEST_GENERATION.md) |
| **Postman-style collections, environments, multi-step flows (vs Python today)** | [COLLECTIONS.md](COLLECTIONS.md) |
| **Registries, PyPI, release promotion** (checklist — same style as [MCP-Bastion](https://github.com/vaquarkhan/MCP-Bastion)) | [DISCOVERY.md](DISCOVERY.md) |
| **Docker / OCI** (images, `ghcr.io` / **GitHub Packages** discovery, Mermaid) | [DOCKER.md](DOCKER.md) |
| **Visual architecture** (Mermaid: CLI → session → test) | [ARCHITECTURE.md](ARCHITECTURE.md) |
| **Visual Studio Code, Cursor, snippets, Markdown “feature” callouts** (preview + Mermaid) | [EDITORS.md](EDITORS.md) · [MARKDOWN_CONVENTIONS.md](MARKDOWN_CONVENTIONS.md) |
| **Why the harness looks like this** (architecture / trade-offs) | [DECISIONS.md](DECISIONS.md) |
| **Gap / implementation checklist** (for maintainers) | [IMPLEMENTATION_CHECKLIST.md](IMPLEMENTATION_CHECKLIST.md) |
| **Releases, upgrades, what changed** | [CHANGELOG.md](../CHANGELOG.md) |
| **PyPI + GHCR release** (tag `v*`, trusted publishing, checklist) | [RELEASING.md](RELEASING.md) |
| **How to contribute** (tests, PRs, release checklist) | [CONTRIBUTING.md](../CONTRIBUTING.md) |
| **Maintainer priorities** (delivery plan; not a public product commitment) | [CONTRIBUTING.md#maintainer-delivery-plan](../CONTRIBUTING.md#maintainer-delivery-plan) |

---

## All documents

| Document | What it is |
|----------|------------|
| [QUICK_START.md](QUICK_START.md) | **Time-to-value:** install, `mcp-test init`, run tests |
| [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) | **Canonical reference** — config, stdio/SSE/HTTP, assertions, fixtures, schema, reporting, plugins |
| [DEVELOPER.md](DEVELOPER.md) | **This repository:** clone, pytest + coverage, module map, link to [examples/](../examples/README.md) |
| [../examples/feature-demo/README.md](../examples/feature-demo/README.md) | **Feature demo packs:** separate folders for functional, regression, and performance examples with report configs |
| [TUTORIAL.md](TUTORIAL.md) | Longer **walkthrough** for new users |
| [CI_AND_REPORTS.md](CI_AND_REPORTS.md) | **CI and reports:** exit codes, JUnit for Actions, when to upload/publish HTML |
| [PERFORMANCE.md](PERFORMANCE.md) | **Performance tests:** `assert_latency` (p95, warmup), `marker(tags=[…])` + `mcp-test -m perf` |
| [PERFORMANCE_TESTING_STRATEGY.md](PERFORMANCE_TESTING_STRATEGY.md) | **Performance product story:** why MCP perf must be protocol-aware, what is in-core vs out-of-scope, and the proposed production-grade roadmap |
| [SECURITY_TESTING.md](SECURITY_TESTING.md) | **Security-first CI strategy:** payloads, auth checks, and leak scanning guidance |
| [CONTRACT_AND_COMPAT.md](CONTRACT_AND_COMPAT.md) | **Compatibility strategy:** contract replay and protocol/client matrix direction |
| [ENTERPRISE_GOVERNANCE.md](ENTERPRISE_GOVERNANCE.md) | **Governance:** audit/policy/tenant requirements, plus practical EU AI Act evidence mapping |
| [PLUGIN_REGISTRY.md](PLUGIN_REGISTRY.md) | **Integrations:** proposed plugin catalog categories and listing template |
| [COMPARISON.md](COMPARISON.md) | **Ecosystem map:** other MCP tools (conformance, evals, benchmarks) and how they fit with Harness + Bastion |
| [LLM_TEST_GENERATION.md](LLM_TEST_GENERATION.md) | **LLMs:** draft tests with review is OK; auto-trusted CI is not; how this differs from LLM-in-the-loop eval tools |
| [COLLECTIONS.md](COLLECTIONS.md) | **Postman / Newman–style** flows: collections + environments, how to do it in **Python** today, **roadmap** for declarative collections; load testing pointers |
| [DISCOVERY.md](DISCOVERY.md) | **Discovery / registries:** internal checklist for releases (PyPI, awesome lists, `server.json`, related tooling) |
| [DOCKER.md](DOCKER.md) | **Container images** — build targets, [PyPI](https://pypi.org/project/mcp-test-harness/) vs **local build**, [GitHub Packages](https://github.com/vaquarkhan?tab=packages) & future **GHCR** |
| [ARCHITECTURE.md](ARCHITECTURE.md) | **Mermaid** high-level and sequence diagrams (how a test run works) |
| [EDITORS.md](EDITORS.md) | **VS Code / Cursor** — `.vscode` snippets, extensions, Mermaid preview |
| [MARKDOWN_CONVENTIONS.md](MARKDOWN_CONVENTIONS.md) | **GitHub/MD** callouts: `[!TIP]` / `**Feature**` blocks, fenced language tags |
| [index.md](index.md) | **Short docs landing** (for GitHub Pages or static site generators) — links into this hub |
| [Dockerfile](../Dockerfile) (repo root) | **OCI image** for `mcp-test` — build/run notes in root [README.md](../README.md#docker) |
| [../server.json](../server.json) (repo root) | **MCP registry / tooling** metadata; bump `version` with [pyproject.toml](../pyproject.toml) on release |
| [CITATION.cff](../CITATION.cff) (repo root) | **Optional citation** — metadata; [LICENSE](../LICENSE) is MIT |
| [DECISIONS.md](DECISIONS.md) | Product and architecture **decision log** |
| [IMPLEMENTATION_CHECKLIST.md](IMPLEMENTATION_CHECKLIST.md) | **Maintainer** checklist for features vs. source locations |
| [CHANGELOG.md](../CHANGELOG.md) | **Version history** (Keep a Changelog; for PyPI / release notes) |
| [RELEASING.md](RELEASING.md) | **Ship a version:** bump files, tag `vX.Y.Z`, PyPI + `ghcr.io` workflows |
| [CONTRIBUTING.md](../CONTRIBUTING.md) | **Contributing** — dev setup, `pytest` + coverage, release checklist; **maintainer delivery plan** (not a public product commitment) |

<p align="center">
  <img src="images/mcp-testobarness-feature.png" alt="MCP Test Harness feature overview" width="85%" />
</p>

**Editor quality-of-life (this repo):** [../.vscode/mcp-test-harness.code-snippets](../.vscode/mcp-test-harness.code-snippets) — VS Code / Cursor snippets (`mcp-assert-tool`, `mcp-test-async`, …).

**Root [README.md](../README.md):** project pitch, feature matrix, **Docker** [Dockerfile](../Dockerfile) / installation, and links back here.

---

## GitHub Pages (optional)

If you enable GitHub Pages for the `docs/` folder, you can set the entry to [index.md](index.md) (short landing with links) or to this [README](README.md) as the main hub, depending on your theme.
