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
| **Why the harness looks like this** (architecture / trade-offs) | [DECISIONS.md](DECISIONS.md) |
| **Gap / implementation checklist** (for maintainers) | [IMPLEMENTATION_CHECKLIST.md](IMPLEMENTATION_CHECKLIST.md) |

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
| [Dockerfile](../Dockerfile) (repo root) | **OCI image** for `mcp-test` — build/run notes in root [README.md](../README.md#docker) |
| [CITATION.cff](../CITATION.cff) (repo root) | **Cite the software** — metadata; [LICENSE](../LICENSE) Section 2 for legal obligations |
| [DECISIONS.md](DECISIONS.md) | Product and architecture **decision log** |
| [IMPLEMENTATION_CHECKLIST.md](IMPLEMENTATION_CHECKLIST.md) | **Maintainer** checklist for features vs. source locations |

**Editor quality-of-life (this repo):** [../.vscode/mcp-test-harness.code-snippets](../.vscode/mcp-test-harness.code-snippets) — VS Code / Cursor snippets (`mcp-assert-tool`, `mcp-test-async`, …).

**Root [README.md](../README.md):** project pitch, feature matrix, **Docker** [Dockerfile](../Dockerfile) / installation, and links back here.

---

## GitHub Pages (optional)

If you enable GitHub Pages for the `docs/` folder, use this [README](README.md) as the documentation hub, or add your own `index` file for your static generator. No separate `index.md` is required for the repository — the hub lives here.
