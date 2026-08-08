# Product roadmap (near-term)

This roadmap groups planned capabilities into practical delivery phases while preserving the core identity of this project:

- **MCP-aware**
- **CI-first**
- **deterministic by default**

## Now (high ROI, low risk)

1. `mcp-test doctor` onboarding and health diagnostics (implemented).
2. HTML report UX polish (grouping, filter, sort, status badges, run metadata).
3. Performance strategy docs and explicit product positioning.
4. Example/demo expansion for feature coverage and discoverability.

## Next (major value unlock)

1. ~~Security baseline assertions~~ — **shipped:** `security_payloads.py`, auth boundaries, unified portal, SARIF export, OWASP rule IDs in JSON/SARIF.
2. ~~MCP trace capture per test and timeline rendering in HTML~~ — **shipped (v1.3):** `trace.py`, `mcp_trace` in JSON/HTML timelines.
3. ~~Tool/resource coverage map~~ — **shipped:** `coverage.py` in JSON/HTML reports.
4. ~~Throughput + baseline-based performance regression gates~~ — **shipped:** `assert_throughput` (`max_p99_ms`, `max_error_rate`), `assert_latency_within_baseline`.
5. ~~Stateless MCP (SEP-2575) dual mode~~ — **shipped:** `mcp-test conformance stateless`, `assert_stateless_throughput`, RFC-006, [TUTORIAL_STATELESS.md](TUTORIAL_STATELESS.md).

## Moat (deterministic CI gate — build these)

Filter: (a) deterministic/reproducible, (b) something a scanner or interactive inspector cannot do well, (c) MCP-specific. No LLM judge, no always-on hosted dashboard, no generic API load farm.

| Tier | Initiative | Status |
|------|------------|--------|
| **1** | **Manifest snapshot / rug-pull gate** — sanctioned baseline of tools/resources/prompts; fail PR on unapproved surface change | **Shipped (this release track):** `manifest_gate:` + `mcp-test manifest` |
| **1** | Persisted history + trend gates (files/artifacts + static Pages report; not a live server) | Next |
| **1** | Determinism / flakiness detector (N-run per-tool scores) | Next |
| **1** | Spec-version + self-version compatibility matrix | Next |
| **2** | Static MCP rule engine (heuristic CI rules; not live threat intel) | Partial via `security_rules` / quality_gate |
| **2** | Contract coverage as a first-class threshold gate | Partial map shipped; threshold gate next |
| **2** | Golden traffic replay (Bastion/proxy → CI) | Later |
| **3** | Governance evidence packs, token/output budgets, regression autobisect | Later |

**Do not build:** LLM playground / model-vs-model scoring; always-on multi-tenant dashboard; out-scanning mcp-scan on general threat research; datacenter-scale generic load testing.

## Later (platform and enterprise)

1. Contract recording/replay and compatibility matrix runs.
2. GitHub Checks/reporter ecosystem integrations.
3. Governance features:
   - signed audit exports
   - role/tenant matrices
   - policy-as-code plugin adapters
4. **Optional (only with clear traction):** local run-history delta (“new findings since last run”) as a **file/SQLite artifact** in CI — not a hosted multi-tenant dashboard. Hosted org dashboards stay out of core.

## Scope guardrails

Core harness should own:

- protocol-aware assertions and CI gates
- reproducible local/CI reports
- opt-in declarative `quality_gate` + OWASP/MCP rule metadata in SARIF/JSON/HTML
- opt-in `manifest_gate` (merge-time MCP surface integrity)

Core harness should not replace:

- distributed load generators
- full observability backends
- org-specific policy engines
- SonarQube / hosted quality SaaS (we emit SARIF into GitHub Code Scanning instead)
- interactive MCP playgrounds or LLM-as-judge accuracy scoring

Those remain integrations/plugins.

**Product naming:** do **not** grow `mcplint` into a Sonar-style scanner brand. `mcplint` remains the optional Bastion version shim; the CI quality gate is `mcp-test` + `quality_gate:`.

## Where we see the most value (prioritized)

Strategic bets that turn the harness from a test library into the **pre-production gate** for MCP servers — one config, one run, one published artifact.

| Priority | Initiative | Why it matters | Delivery fit |
|----------|------------|----------------|----------------|
| **1** | **Unified report portal** — one artifact per run combining functional, perf, security, and resiliency scores | High visibility where developers and buyers look (PRs, releases, compliance packets); builds on existing console / JUnit / JSON / HTML reporters | **Shipped (v1.2):** `unified_summary` in JSON/HTML; category scores by `@marker` tags |
| **2** | **Security payload packs** — prompt injection, traversal, leak scanner, Suite A egress/covert as `@marker(tags=["security"])` | Strong enterprise wedge; auditable evidence for governance programs without turning core into a runtime WAF | **Shipped (v1.2 + Suite A):** `security_payloads.py` — injection/path/leak packs plus `assert_egress_quarantined`, `assert_egress_allowed`, `assert_covert_channel_neutralized`, `assert_general_exec_tools_absent` |
| **3** | **Resiliency assertions** — `assert_reconnects`, `assert_survives_crash`, `assert_degrades_gracefully` | Underserved and MCP-specific; agent workflows amplify crash, timeout, and partial-failure modes | **Shipped (v1.2):** `resiliency.py` |
| **4** | **Coverage map** — e.g. “12 tools advertised, 8 tested, 2 never called, 2 missing auth tests” | Huge DX win; closes the gap between `tools/list` and what CI actually exercises | **Shipped (v1.2):** `coverage.py` — auto-tracked per run, in JSON/HTML `coverage` + gaps |
| **5** | **Load testing (SLO-oriented)** — `assert_throughput` + baselines, not a full load generator | Validates time-to-answer in the same MCP-aware tests as correctness; defer datacenter-scale RPS to k6/Locust integrations | **Shipped (v1.2):** `baselines.py`; **stateless hyperscale (RFC-006):** `assert_stateless_throughput` |
| **6** | **Resiliency experiment catalog** — AWS FIS-style templates, stop conditions, scorecard | Turns chaos/resiliency primitives into click-and-go CI gates; feeds Resilient conformance level | **Shipped (v2.1):** `mcp-test experiment`, bundled `catalog.yaml`, RFC-005 |
| **7** | **Conformance levels + `mcp-test try`** — badge seal and zero-config probe | Self-propagating adoption; README badge + PR gate language | **Shipped (v2.2+):** RFC-002, Marketplace Action |
| **8** | **Record to suite + pre-commit** — live calls → tests; Boot/Protocol before push | Kills write-the-tests barrier; habit loop | **Shipped (v2.4):** RFC-001 `mcp-test record`, `.pre-commit-hooks.yaml` |

### How this maps to phases

- **Now:** SLO-oriented perf (`assert_latency`, `assert_throughput`), HTML report polish, demos.
- **Next:** unified run summary in HTML/JSON, security payload packs, coverage map, baseline perf gates, first resiliency assertions.
- **Later:** ~~GitHub PR commentary~~ **shipped (v1.2):** composite action `pr-comment` input; **protocol-aware chaos** **shipped (v1.3):** `chaos.py`; **offline test generate** **shipped (v1.3):** `mcp-test generate`; **experiment catalog** **shipped (v2.1):** `mcp-test experiment`; **record-to-suite** **shipped (v2.4):** `mcp-test record`; signed audit exports, contract replay, transport-level fault templates.

Companion tools stay complementary: [MCP-Bastion](https://github.com/vaquarkhan/MCP-Bastion) for runtime defense; external load generators for extreme scale; LLM eval frameworks for non-deterministic agent quality (see [COMPARISON.md](COMPARISON.md)).

