# Changelog

All notable changes to this project are documented in this file. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **HTML scan report UI:** sticky scan TOC, quality-gate scorecard, full security findings table (severity/OWASP/framework/file + client severity filter), MCP contract-coverage % ring and coverage issue rows — still a self-contained CI artifact (no hosted dashboard).

## [4.0.0] - 2026-08-02

### Added

- **Manifest / rug-pull gate** (`manifest_gate:` + `mcp-test manifest`): deterministic snapshot of the full MCP surface (tools/resources/prompts schemas + capabilities) that fails CI when the sanctioned baseline changes without `--update-snapshots` / `mcp-test manifest update`. Merge-time supply-chain control, not runtime detection.
- **Declarative quality gate** (`quality_gate:` in mcp-test.yaml): `require_security_tests`, `fail_on_severity`; emits `unified_summary.quality_gate` alongside SARIF/HTML and can fail CI when security tests were skipped.
- **Expanded security rule catalogue** (OWASP-MCP, OWASP-LLM, agentic themes) in `security_rules.py` with `list_rules()` for report correlation.

### Fixed

- **`mcp-test generate`:** docstring closers were truncated to `.""` (SyntaxError); now emit valid `"""`.
- **`--update-snapshots`:** CLI flag is applied at runtime so corrupted/outdated `.snap` files are rewritten (was parsed into config but ignored).

### Changed

- **Major version 4.0.0** — CI quality gate + MCP surface integrity are first-class product surfaces; all **23** PyPI artifacts and Marketplace Action pins align at **4.0.0**.

## [3.0.10] - 2026-08-01

### Added

- **Real provider helpers** on all framework packages: tool assertion with optional text check, MCP→provider schema converters, and `mcp-test.yaml` config builders (FastMCP pattern).
- **Five new PyPI packages:** `mcp-test-harness-ollama`, `-openrouter`, `-litellm`, `-xai`, `-autogen`.
- `scripts/sync_provider_packages.py` to regenerate/align vendor packages.

### Changed

- **All 23 PyPI artifacts** aligned at **3.0.10** (core + 22 shims).
- Marketplace Action and docs examples pin **`@v3.0.10`**.
- Declare **`httpx`** as a core dependency (stateless gate / Quick CI).
- Pin **`mcp>=1.0.0,<2`** until the harness is migrated to MCP Python SDK 2.x (`fastmcp` / client API moves).

## [3.0.9] - 2026-07-24

### Added

- **CRA alignment (opt-in, non-breaking):** `.github/SECURITY.md` Article 14-oriented VDP; CycloneDX SBOM steps on `publish.yml` / `docker-publish.yml` (fail-safe artifacts); `CRATechnicalDocumentReporter` via `--cra-output` / `report.cra_output`; [docs/CRA_COMPLIANCE.md](docs/CRA_COMPLIANCE.md) + [cra-evidence-flow.svg](docs/images/cra-evidence-flow.svg).

### Changed

- **All 18 PyPI artifacts** aligned at **3.0.9**.
- Marketplace Action and docs examples pin **`@v3.0.9`**.

## [3.0.8] - 2026-07-21

### Added

- **Stateless MCP (SEP-2575 / RFC-006):** dual-mode support alongside existing stateful flows — `mcp-test conformance stateless`, `assert_stateless_throughput`, adversarial header/schema gate, hyperscale URL-direct load (httpx, no new deps).
- **Documentation:** [TUTORIAL_STATELESS.md](docs/TUTORIAL_STATELESS.md), RFC-006 design doc, examples + `feature-demo/stateless-testing/` demo pack.
- **Visual:** [stateless-dual-mode.svg](docs/images/stateless-dual-mode.svg) — stateful vs stateless architecture diagram (docs + website).

### Changed

- **All 18 PyPI artifacts** aligned at **3.0.8**.
- Marketplace Action and docs examples pin **`@v3.0.8`**.

## [3.0.7] - 2026-07-11

### Added

- **Product website:** integrations page with live 18-package download widget, features deck (print-to-PDF), visual guide gallery, Record→Generate→Gate and shipped-features sections.
- **README badge row** on website top bar and hero (PyPI, CI, tests, coverage, GHCR, Website).

### Changed

- User-facing copy uses **Website** instead of GitHub Pages; README adds Website badge.
- **All 18 PyPI artifacts** aligned at **3.0.7**.
- Marketplace Action and docs examples pin **`@v3.0.7`**.

## [3.0.6] - 2026-07-11

### Fixed

- **GitHub Pages PyPI stats bar:** deploy `html/` as site root via GitHub Actions; always-visible badge bar (version, total downloads, Python versions); nav offset below bar; legacy `/html/*` redirects.

### Added

- **SPONSORS.md** and **`.github/FUNDING.yml`** with sponsor links in README and CONTRIBUTING.

### Changed

- **All 18 PyPI artifacts** aligned at **3.0.6**.
- Marketplace Action and docs examples pin **`@v3.0.6`**.

## [3.0.5] - 2026-07-11

### Added

- **GitHub Pages PyPI stats bar:** live widget on all site pages (`html/assets/pypi-stats.js`) - fetches pepy.tech total + rolling 30-day downloads and current PyPI version on each visit (fixes stale ~3k monthly badge vs ~10k total).

### Changed

- README and package table download badges use pepy **total** downloads (not CDN-stale `/month` image).
- **All 18 PyPI artifacts** aligned at **3.0.5**.
- Marketplace Action and docs examples pin **`@v3.0.5`**.

## [3.0.4] - 2026-07-10

### Fixed

- **GitHub Action:** correct `actions/github-script@v8.0.0` commit pin (typo broke `dist-smoke` CI). **Distribution smoke** now green on `main`.

### Changed

- **All 18 PyPI artifacts** aligned at **3.0.4**.
- Marketplace Action and docs examples pin **`@v3.0.4`**.

## [3.0.3] - 2026-07-10

### Added

- **Browserless 100% coverage:** [`tests/test_browser_and_edge_coverage.py`](tests/test_browser_and_edge_coverage.py) mocks PDF/screenshot browser paths and covers `_capability_subset` / `_unwrap_session` / record `isError` edge branches so `--fail-under=100` passes without Chrome/Edge.
- **CI coverage gate** on every PR (`validate` quick job) and on full main runs.
- **Distribution smoke job:** GHCR `docker run … --version`, PyInstaller binary `--version`, sample provider shim imports, and composite GitHub Action `try-mode` against the minimal fixture.

### Changed

- CONTRIBUTING: removed environment-dependent browser caveat; gate is required on clean checkouts.
- **All 18 PyPI artifacts** aligned at **3.0.3**.
- Marketplace Action and docs examples pin **`@v3.0.3`**.

## [3.0.2] - 2026-07-10

### Changed

- **README feature map:** renamed to **What ships end-to-end** (no release-number heading); added CLI, automation, Docker, and pre-commit/plugin hooks rows; dropped inline version labels from that map and Core Features.
- **All 18 PyPI artifacts** aligned at **3.0.2**.
- Marketplace Action and docs examples pin **`@v3.0.2`**.

## [3.0.1] - 2026-07-10

### Added

- **Seam / contract e2e suite:** [`tests/test_seam_e2e.py`](tests/test_seam_e2e.py) + rich fixture [`tests/fixtures/rich_mcp_server.py`](tests/fixtures/rich_mcp_server.py) - record round-trip (`ast.parse` + run), README `assert_capabilities({"tools": {}})` against a real server, coverage `tools_tested > 0`, init→run onboarding, redirected cp1252 `--help`. Documents the H/I/J class of boundary bugs that line coverage alone misses ([CONTRIBUTING.md](CONTRIBUTING.md)).

### Changed

- **All 18 PyPI artifacts** aligned at **3.0.1**.
- Marketplace Action and docs examples pin **`@v3.0.1`**.

## [3.0.0] - 2026-07-10

### Changed

- **Major release (semver 3.0.0):** production-hardening pass after 2.4.0 - onboarding, Windows, conformance integrity, coverage map, and record codegen.
- **All 18 PyPI artifacts** aligned at **3.0.0**.
- **README audience sections:** opening now leads with C-suite/directors, then architects/tech leads, then developers; remaining reference content unchanged.
- **Docs freshness:** test-count badges and copy updated to **835+** / current suite size; em/en dashes replaced with ASCII hyphens in README and dogfood SVG.
- Marketplace Action and docs examples pin **`@v3.0.0`**.

### Fixed

- **Coverage completeness:** `assert_tool_rejects`, `assert_tool_idempotent`, resiliency helpers, and security payload assertions now call `record_tool_call` so tools exercised only through those paths appear in the coverage map.
- **`mcp-test record` error tools:** MCP `isError` responses emit `assert_tool_rejects` tests (not false happy-paths); transport-only failures are still skipped.
- **`mcp-test record` codegen (BUG H):** recorded test docstrings now close with three quotes (was `.""`, a SyntaxError that made recorded suites undiscoverable).
- **`assert_capabilities` subset (BUG I):** empty/partial nested expected values mean "present" (e.g. `{"tools": {}}` matches FastMCP `{"tools": {"listChanged": false}}`), matching the docstring and README example.
- **Coverage map / Covered level (BUG J):** coverage state is stored on the unwrapped ClientSession so per-test TracedSession/ChaosSession wrappers no longer leave `tested.tools` empty.
- **Empty discovery (BUG F):** `No tests discovered` now exits **5** (stderr), matching pytest's no-tests-collected gate so CI cannot green-pass a misconfigured `test.dirs`.
- **Windows quoted `server.command` (BUG G):** `split_server_command` strips surrounding quotes after `shlex.split(posix=False)` so paths with spaces spawn correctly.
- **`--report-output` without `--report-format`:** emit a stderr warning instead of a silent no-op.
- **`experiment run` unknown id:** error message no longer double-quoted via `KeyError` `str()`.
- **`mcp-test init` config:** scaffold now writes nested `test.dirs` (valid schema) instead of top-level `test_dirs`.
- **`--sarif-output`:** always writes when set (previously skipped when `--report-format sarif`).
- **Windows console encoding:** UTF-8 stdout/stderr at CLI entry; ASCII-safe help strings so `--help` / doctor no longer crash on cp1252.
- **Conformance CLI (BUG D):** `--report` works with both `grade` and `badge` in either position.
- **Conformance badge (BUG E):** `badge --report` uses the same graded level as `grade` (no unearned Covered seal).

## [2.4.0] - 2026-07-10

### Added

- **Record to suite (RFC-001):** `mcp-test record` captures live tool calls (or `--from-json` cassette) into reviewable tests + `__snapshots__`.
- **pre-commit hook:** `.pre-commit-hooks.yaml` (`mcp-test-try`) and [examples/pre-commit-config.yaml](examples/pre-commit-config.yaml).
- Design doc: [docs/design/RFC-001-record-to-suite.md](docs/design/RFC-001-record-to-suite.md).
- Marketplace listing documented; Action examples pin `@v2.4.0`.

### Changed

- **All 18 PyPI artifacts** aligned at **2.4.0**.
- Tier 1 adoption items marked shipped in ROADMAP_GROWTH.

## [2.3.0] - 2026-07-09

### Added

- **Inspector pairing docs:** local sandbox (MCP Inspector) → graduate to harness tests → CI loop in [docs/COMPARISON.md](docs/COMPARISON.md).

### Changed

- Docs and Action examples pin **`@v2.3.0`** / `mcp-test-harness==2.3.0`.
- **All 18 PyPI artifacts** aligned at **2.3.0**.

## [2.2.0] - 2026-07-09

### Added

- **Conformance levels + badge (RFC-002):** Boot to Protocol to Covered to Secure to Resilient scorecard on every run (`unified_summary.conformance`).
- **`mcp-test try`** — zero-config conformance probe (handshake + schema); optional `--suite core` experiments.
- **`mcp-test conformance grade|badge`** — grade a JSON report or print a README shields.io badge snippet.
- HTML Conformance panel and PR summary conformance line.
- GitHub Action outputs `conformance-level` / `conformance-level-num`; root `action.yml` for Marketplace (`owner/repo@tag`); `try-mode` / `pr-comment`.
- Design docs: RFC-002, ROADMAP_GROWTH.md.
- Showcase: grade public servers such as AWS RODA MCP (`uvx awslabs.roda-mcp-server@latest`).

### Fixed

- **Dogfood SVG:** repaired invalid characters in `docs/images/dogfood-e2e.svg` so the README diagram renders.

### Changed

- **All 18 PyPI artifacts** aligned at **2.2.0**.

## [2.1.0] - 2026-07-09

### Added

- **Resiliency experiment catalog (RFC-005):** AWS FIS-style ready-to-run experiments with guardrails and a scorecard.
- **`mcp-test experiment list`** — browse bundled templates (`latency-injection`, `crash-mid-call`, `reconnect-storm`, and more).
- **`mcp-test experiment run <id>`** and **`mcp-test experiment run --suite core`** — compile catalog YAML to chaos/resiliency tests and run against your server.
- **`mcp-test experiment scorecard`** — print resiliency grade from JSON report output.
- **HTML report:** Resiliency experiments panel with hypothesis, pass/fail, grade, and copy-run buttons.
- **Design doc:** [docs/design/RFC-005-resiliency-experiments.md](docs/design/RFC-005-resiliency-experiments.md).

### Changed

- **All 18 PyPI artifacts** aligned at **2.1.0**: `mcp-test-harness` plus 17 optional `mcp-test-harness-*` provider packs under `packages/`.

## [2.0.2] - 2026-07-06

### Added

- **HTML dashboard v2:** self-contained report with product branding, stat cards, pass-rate donut, run timeline, top failures, slowest tests, platform QA panels (chaos monkey, load/SLO, MCP-Bastion security pairing), unified portal, coverage map, and tags matrix.
- **Interactive filters:** status chips, search, date/time range, duration min/max, live “showing X of Y” summary with stat-card recalculation.
- **Export & theme:** light/dark theme (persisted), **Save as PDF** (print CSS), **Export CSV** (UTF-8 BOM + ISO timestamps for Excel), keyboard shortcuts (`/`, `Esc`, `t`, `?`).
- **`mcp-test export-pdf`** and **`--pdf-output`** for headless Chrome/Edge PDF summaries (JMeter-style).
- **`capture_html_screenshot()`** in `pdf_export.py`; `build_sample_html.py` regenerates README/Pages screenshots when a browser is available.
- **GitHub Pages:** hosted [sample HTML report](https://vaquarkhan.github.io/mcp-test-harness/reports/sample_mcp_test_report.html), product images, updated examples/index.
- **Docs:** README Reports section uses live `html-dashboard.png` screenshot; `report-formats.png` retained as multi-format infographic.
- **HTML report UI:** live Console/JUnit/JSON format previews from run data with click-to-expand cards in the “Test report outputs” strip.

### Fixed

- **CSV export:** Excel `started` column no longer shows `â€"` junk — uses ISO `data-started-iso`, strips em-dash placeholders, writes UTF-8 BOM.

## [2.0.1] - 2026-07-06

### Fixed

- **CallToolResult.isError:** assertions now read `isError` on the MCP result object (per spec and FastMCP), not only on content items. Fixes false passes in `assert_tool_call`, false failures in `assert_tool_rejects` / `assert_tool_denied`, and `assert_degrades_gracefully` misfires against spec-compliant servers.

## [2.0.0] - 2026-07-06

### Changed

- **Major release (semver 2.0.0):** bundles v1.2 platform QA (coverage map, unified portal, SARIF, security payloads, baselines) and v1.3 diagnostics (MCP trace, chaos, `mcp-test generate`), e2e dogfood, and 100% coverage CI gate.
- **All 18 PyPI artifacts** aligned at **2.0.0**: `mcp-test-harness` plus 17 optional `mcp-test-harness-*` provider packs under `packages/`.
- **Docker / GHCR** images tagged **`2.0.0`**, **`2.0.0-dev`**, **`latest`**, and **`dev`** on `v2.0.0` git tag.
- **`SessionResults.harness_version`** now tracks `mcp_test_harness.__version__` (no hardcoded scheduler string).

### Added

- **Bulk optional-package publish** on `v*` tags via [`.github/workflows/publish.yml`](.github/workflows/publish.yml) matrix job.

## [1.3.0] - 2026-07-05

### Added

- **MCP trace capture:** per-test JSON-RPC event log (`mcp_trace`) with stdio pollution hints; interactive timeline in HTML reports.
- **Protocol-aware chaos:** `@marker(tags=["chaos"], chaos_faults=[...])` — delay, 503, truncate, schema drift on `call_tool`.
- **`mcp-test generate`:** offline schema-driven test scaffolding from live `tools/list` (+ optional `--drift-report`).
- **E2E dogfood:** `tests/test_harness_dogfood_e2e.py` runs the real `mcp-test` CLI against bundled FastMCP fixtures; CI enforces `coverage report --fail-under=100` on every PR and uploads coverage HTML + dogfood smoke report on `main`.
- **Docs/images:** [`docs/images/dogfood-e2e.svg`](docs/images/dogfood-e2e.svg); README and [DEVELOPER.md](docs/DEVELOPER.md) dogfood sections.
- **Developer examples (v1.3):** [example_mcp_trace.md](examples/example_mcp_trace.md), [example_chaos_testing.md](examples/example_chaos_testing.md), [example_generate_scaffold.md](examples/example_generate_scaffold.md), [platform-qa demo pack](examples/feature-demo/platform-qa/README.md).

### Fixed

- **GitHub Pages:** deploy only `html/` (with `.nojekyll`) instead of the entire repository; fixes failed `pages-build-deployment` runs.

## [1.2.0] - 2026-07-05

### Added

- **Platform QA (v1.2):** `coverage.py`, `security_payloads.py`, `resiliency.py`, `baselines.py`, `unified_report.py` — coverage map, security payload packs, resiliency assertions, baseline perf gates, unified portal in JSON/HTML.
- **`assert_throughput` SLO params:** `max_p99_ms` and `max_error_rate` alongside `min_rps`.
- **SARIF export:** `--report-format sarif` or `--sarif-output` for GitHub Code Scanning; OWASP MCP rule metadata on security findings (`security_rules.py`).
- **PR summary:** `--pr-summary-output` markdown; GitHub Action `pr-comment` input posts/updates PR comments.
- **Docs:** [POSITIONING.md](docs/POSITIONING.md), updated [COMPARISON.md](docs/COMPARISON.md), [SECURITY_TESTING.md](docs/SECURITY_TESTING.md), README visuals.

## [1.1.0] - 2026-04-25

### Added

- **`assert_throughput`:** concurrent `call_tool` load-style checks with optional minimum **RPS** budget (complements `assert_latency`).
- **CLI:** `--fail-fast` (stop after first failure, error, or timeout), `--last-failed` (re-run from `.mcp_test_harness/last-failed.json`); stricter list/config handling as documented in [RELEASING](docs/RELEASING.md).
- **Scheduler:** **LPT (greedy) assignment** of whole test modules to parallel workers; shared fail-stop for parallel `--fail-fast`.
- **Config:** validate `mcp-test.yaml` / `mcp-test.toml` before `HarnessConfig` load (clear aggregated errors, exit 2 on failure).
- [`.github/workflows/docker-publish.yml`](.github/workflows/docker-publish.yml) — on **`v*`** tags, build and push **runtime** and **dev** images to **GHCR** (`ghcr.io/vaquarkhan/mcp-test-harness`). [docs/RELEASING.md](docs/RELEASING.md) documents PyPI + Docker release steps with GitHub settings.
- [docs/LLM_TEST_GENERATION.md](docs/LLM_TEST_GENERATION.md) — guidance on **LLM-assisted** test drafting vs **automatic** “connected LLM” generation in CI; linked from [COMPARISON](docs/COMPARISON.md) and the [docs hub](docs/README.md).
- **Docs:** [DEVELOPER.md](docs/DEVELOPER.md#stdio_mcp-and-the-coverage-gate) — **stdio_mcp.py** and the **100%** `coverage` fail-under: intentional `omit` (maintainer policy), **integration** coverage, and production-grade quality for the **rest** of `mcp_test_harness` under the gate.
- An expanded [examples](examples/README.md) set: [assertions_async_demo.py](examples/assertions_async_demo.py), [validate_mcp_test_config.py](examples/validate_mcp_test_config.py), [sample_mcp_test.yaml](examples/sample_mcp_test.yaml), [patterns_mcp_test.md](examples/patterns_mcp_test.md). Cross-links from the [docs hub](docs/README.md), [README](README.md), and [DEVELOPER_GUIDE](docs/DEVELOPER_GUIDE.md).
- [docs/COLLECTIONS.md](docs/COLLECTIONS.md) — **Postman / Newman–style** multi-step flows, environments, and how to express them in **Python** today; **roadmap** for optional declarative collections; linked from [COMPARISON](docs/COMPARISON.md) and the [docs hub](docs/README.md).
- [examples/FEATURES_INDEX.md](examples/FEATURES_INDEX.md) and **per-feature** `example_*.md` / `mcp_test_*.yaml` in [examples](examples/) so every README *core* feature has a **dedicated** sample; [examples/README.md](examples/README.md) expanded.

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
