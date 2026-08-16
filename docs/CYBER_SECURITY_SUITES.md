# MCP Test Harness — Cyber-Security Suites and Backlog (Consolidated)

**Single source** for harness cyber-security work: what is already implemented, what remains open (nature-filtered), assurance reports definition, and research grounding.

**Companion (runtime):** `MCP-BASTION-CYBER-EXTENSIONS.md` in the Bastion repo. **No third file.**

**Honest framing (binding):** green means the encoded corpus is caught *reproducibly* in CI — not that the system is safe against a novel adaptive adversary, and not live compliance.

---

## Guiding principle (unchanged)

Deterministic, CI-gateable, reproducible assertions that emit SARIF / JUnit / JSON with OWASP metadata. Every Bastion extension is “done” only when it has a matching suite **here**.

### Nature (keep — do not change)

| Constraint | Rule |
|------------|------|
| Stack | Python, `requires-python >= 3.10`, `src/mcp_test_harness/`, hatchling |
| Tests | Pytest `asyncio_mode = "auto"`, coverage `fail_under = 100` |
| Assertions | Prefer `assert_*`, session-first async where MCP I/O; `MCPAssertionError` |
| Markers | Declared in `pyproject.toml`; gated path has **no hard live-model dependency** |
| Determinism split | **Gated:** recorded-verdict / fixture enforcement + deny codes. **Nightly** (`semantic_live` / `adaptive`): detection-quality only — reported, never gated |
| Scope | Controlled server-under-test only — **never** live third parties |

Never report “semantic egress tested” from plumbing tests alone.

---

## Selection verdict (this consolidation)

Only items that **preserve** the nature above are **Chosen**. Items that would turn the harness into a live red-team, hosted dashboard, live-model PR gate, or third-party attacker are **Rejected**. Borderline community ideas are **Deferred / candidate** until a Bastion control exists and a fixture design is ready.

| Bucket | Meaning |
|--------|---------|
| **Chosen** | May be implemented on follow-up PRs; stays CI-native and deterministic (or nightly-only where stated) |
| **Deferred** | Compatible in principle; wait for Bastion pairing or keep scope tiny |
| **Rejected** | Changes product nature or violates no-offensive / no-live-gate rules — do not build |

---

## 1. Already implemented (done — do not re-propose)

Verified against merged `main` (Suite A/B track + later PRs including v5.0 load + v5.1 agent scan).

| Capability | File(s) | Notes |
|------------|---------|--------|
| Suite A: semantic egress packs | `security_payloads.py`, `tests/test_security_egress.py` | `assert_egress_quarantined`, `assert_egress_allowed`, social-engineering + AISI fixture, `assert_general_exec_tools_absent` |
| Suite B (partial): known-encoding covert | `security_payloads.py` | `assert_covert_channel_neutralized`, `COVERT_CHANNEL_PAYLOADS` |
| Injection / path / leak | `security_payloads.py` | `assert_injection_blocked`, `assert_path_traversal_blocked`, `assert_no_secret_leak` |
| OWASP mapping + SARIF | `security_rules.py`, `sarif_reporter.py` | Incl. `semantic-egress-quarantine`, `covert-channel-known-encoding`, `capability-reduction-exec` |
| Quality + manifest gates | `quality_gate.py`, `manifest_gate.py` | Opt-in; rug-pull surface snapshot |
| AGENTS.md hidden-Unicode scan | `agents_md_scan.py` | `assert_agents_md_clean`, `mcp-test scan-agents`, opt-in `agents_md_gate:` (v5.1) |
| Load primitives (partial) | `assertions.py` | `assert_throughput` (weighted `calls`, `duration_s`, p90/p95), `assert_load_phases` (warmup excluded) |
| Reserved nightly markers | `pyproject.toml`, `security-nightly.yml` | `semantic_live`, `adaptive`; empty collection (exit 5) = success until suites land |
| Hygiene | `pyproject.toml` `testpaths=["tests"]` | Root pytest does not collect `examples/` |

**Baseline expectation:** full `pytest` + `fail_under = 100` must stay green on every security PR.

---

## 2. Open backlog — Chosen (nature-safe)

Priority order for implementation PRs (cheap / high pairing first):

1. Audit-chain verifier  
2. Suite D — **deterministic** parts only  
3. Load-resilience remainder (deny-code / control-engagement)  
4. Incident-driven conformance E–K (fixtures)  
5. Suite C attestation (when Bastion Ext C is ready)  
6. Suite B remainder — **capacity first**; media known-carriers only  
7. Assurance evidence + OSCAL **assessment-results** (harness half only)  
8. Structural RCE-precondition rules + standards tags  
9. Nightly `adaptive.py` (reported only)  
10. Optional Numbat **fixture ingestion** contract  

### 2.1 Audit-chain verifier — **Chosen** (P0)

Pairs with Bastion Extension F output.

- `assert_audit_chain_intact(records)`: recompute SHA-256 chain (genesis `prevHash` = 64 zero hex), fail on broken link / tamper / truncation / reorder  
- Optional CLI: `mcp-test audit verify <file>`  
- Target: `assertions.py` (or small `audit_chain.py`) + `tests/test_audit_chain.py`  
- **Limit:** proves records were not altered undetected — not that none were omitted  

### 2.2 Suite D — deterministic only — **Chosen** (P0)

Pairs with Bastion Extension D residual.

| In | Out |
|----|-----|
| `assert_untrusted_context_quarantined(resource)` (markers present) | `assert_no_cross_agent_influence` as **PR gate** |
| `assert_context_evicted_on_complete(session)` | Live multi-agent model evals |
| Cross-tenant read denied (fixture) | IFC / dual-LLM architecture validation |

Target: `tests/test_cross_agent.py` + assertions. Residual IFC case = documented fixture / `in_scope=false`, not a silent pass.

### 2.3 Load / resource-exhaustion resilience — **Chosen** (P1)

Pairs with Bastion load-resilience caps. **Availability is a security property.**

**Already shipped (do not rebuild):** weighted multi-tool `calls`, phased ramp via `assert_load_phases`.

**Still missing (add):**

- Error-kind + deny-code breakdown: `tool_error` / `rpc_error` / `timeout` / `exception` + `RATE_LIMITED` / `CONCURRENCY_LIMIT` / `LOAD_SHED` / `CIRCUIT_OPEN` in unified report  
- `assert_control_engages_under_load` — dominant deny is the availability control, not timeout/exception  
- `assert_no_fail_open_under_load`  
- `assert_fairness_under_load` (fixture tenants)  
- `assert_latency_slo_until_shed` (admitted calls only)

**Gate:** control engagement + no-fail-open. **Report, do not PR-gate:** absolute RPS / p99.  
Target: extend `assertions.py` + `tests/test_load_resilience.py`; optional `load` marker.  
**Do not** depend on third-party load labs or cite them as product inspiration in docs.

### 2.4 Incident-driven conformance (E–K) — **Chosen** (P1)

Fixture-driven, gated, controlled SUT only. Extends blunt packs with CVE-class cases:

| ID | Theme | Assert direction |
|----|--------|------------------|
| E | Path + symlink escape | Reject `../`, absolutes, symlinks |
| F | Command injection | No exec / no echo of metacharacters |
| G | DNS-rebinding / transport binding | Non-loopback bind / bad Origin rejected |
| H | Supply-chain manifest hash | Hash ≠ pin → denied |
| I | Link-unfurl / encoded-URL exfil | Bounded or denied |
| J | Memory poisoning (ASI06) | Protected keys denied; injection markers caught |
| K | Benchmark egress / solution exfil | Egress quarantine + no general exec (A already covers exec) |

### 2.5 Suite C — attestation conformance — **Chosen** (P2, Bastion-paired)

`assert_unattested_server_denied`, `assert_envelope_verified`, `assert_tampered_request_rejected`, `assert_unauthorized_sampling_dropped`, `assert_tool_allowlist_deny_by_default`, plus both polarities when attestation is advisory vs required.  
Target: assertions + `tests/test_attestation_conformance.py`. Proves mechanism, not intent.

### 2.6 Suite B remainder — **Chosen** (P2)

| Prefer first | Notes |
|--------------|--------|
| `assert_capacity_enforced(sink, bytes)` | Content-agnostic; durable; pairs CapacityLedger |
| `assert_unsigned_media_suspect` / `assert_signed_media_exempt` | **Known carriers only** — not “all stego gone” |

### 2.7 Assurance evidence / metrics / OSCAL assessment-results — **Chosen** (P2)

Harness is the **assurance half** (Bastion owns catalog / obligation / live chain).

- `evidence.py`: `ControlEffectivenessRecord`, `CoverageMatrixEntry` — `proven` **only** from gated deterministic path; nightly never flips `proven`; OOB exec `in_scope=false`  
- `metrics.py`: gated `control_effectiveness`, `owasp_coverage`, `suite_pass_rate`; nightly `adaptive_success_rate`, `detection_rate`, `false_positive_rate`  
- `oscal.py`: **assessment-results only** (observations/findings); do **not** author catalog/profile; schema-validate or fail generation  
- Reports: R6 control effectiveness, OWASP MCP coverage matrix, conformance scorecard with gated vs nightly **visually separated**  
- Artifacts: HTML/JSON/JUnit/SARIF/OSCAL; nightly numbers as **separate** artifacts  

### 2.8 Structural RCE-precondition rules + Hub-shaped pack — **Chosen** (P2)

Extend `manifest_gate` / `quality_gate` with deterministic schema rules (`unbounded-string-param`, `missing-input-schema`, `destructive-without-constraints`). Emit as risk signals, not confirmed exploits. Each gated rule needs a fixture + false-positive test.

### 2.9 Confused-deputy / scoped-credential / pre-tool-hook — **Chosen** (P2–P3)

Fixture-driven only: audience / no passthrough / over-privileged enum denied; scope owner/expiry/audience; hook fails closed on no-rule / unknown server / unreachable decision. Mark “agent ignores hooks” residual as `in_scope=false`.

### 2.10 Adaptive trend module — **Chosen as nightly only** (P3)

`adaptive.py`: seeded mutation generator (pin seed + version), emits `attack_success_pct` / `detection_pct` under `adaptive` marker. Helpers `assert_detection_rate` / `assert_false_positive_rate` under `semantic_live`. **Never a PR gate.** Number = version-pinned lower bound / regression signal.

### 2.11 Endpoint (Numbat) ingestion contract — **Chosen optional** (P3)

Static `numbat_findings.ndjson` fixtures only. Assert mapped evidence is `source=numbat`, `out_of_band=true`, `in_scope=false`, and **never** a governed deny / proven control. No live Numbat, no OS hooks.

### 2.12 Reporting organization — **Chosen** (P3)

Trust-boundary evidence matrix + launch-gate readiness page as **report organization** over existing suites. Must say: technical evidence only — not certification, not “safe.”

### 2.13 Standards tagging — **Chosen** (P3)

Emit AISVS C-ids and MITRE ATLAS technique ids alongside OWASP MCP / ASI ids in `security_rules` / SARIF / coverage matrix / OSCAL assessment-results.

---

## 3. Deferred / candidate (compatible later, not next)

| Item | Why deferred |
|------|----------------|
| Package / dependency hallucination corpus | Mechanism-only, corpus goes stale; keep tiny if ever added |
| Free “MCP security grade” aggregator of external scanners | Base-rate checks OK; **ingested third-party SARIF must stay reported-only, never gated** |
| Component inventory report | Discovery, not assurance — separate from `proven` counts |
| Recommendation-poisoning fixtures | Extends Suite D / memory; after D lands |
| Full Hub community rule marketplace | Needs contribution bar (fixture + FP test) before any community rule is `gated` |

---

## 4. Rejected (do not build — would change nature)

| Item | Reason |
|------|--------|
| Live offensive testing / pentest against third parties | Explicitly out of harness jurisdiction |
| Adaptive / detection-quality as PR merge gates | Flaky; violates determinism split |
| Live Numbat / OS-hook / live-agent monitoring invocation | Breaks no-infra gated path |
| Multi-engine scanner aggregation as a **gate** | Imports foreign flakiness into CI |
| IFC / dual-LLM architecture validation | Belongs with that reference implementation |
| Claiming ASI07 (A2A) or direct OOB exec as **proven** here | `in_scope=false` only |
| Live red-team consoles / autonomous exploit runners | Product is a CI gate, not Strix-class offense |
| Authorship of OSCAL catalog/profile or Bastion R5/R10 live chain | Compliance / runtime layers, not harness |
| Kernel/OS sandbox validation beyond fixtures | Out of library scope |
| Tunnel / hosted infra features | Out of nature |

---

## 5. Not in the harness (state explicitly)

- Live offensive testing against real third parties (AISI behaviors = local fixtures only)  
- Kernel/OS sandbox validation beyond fixtures  
- IFC / dual-LLM architecture validation (residual fixtures that *motivate* it are OK)  
- Hosted-infrastructure misconfiguration and secret-vault storage (delegated by design)  

---

## 6. OWASP MCP + ASI mapping (honesty)

- Each MCP01–MCP10 item maps to a **shipped** or **Chosen backlog** suite (see §2 / §1).  
- ASI01–ASI10: gated where deterministic; nightly for detection quality; ASI07 and direct OOB half of ASI10 = `in_scope=false` with reason.  
- `proven` never comes from a nightly pass.

---

## 7. Research grounding (compact)

Paraphrased shared grounding with the Bastion companion; detection numbers are **lower bounds**:

- AISI-class polite PR + OOB exec → permanent regression fixture (done: `AISI_MAINTAINER_PRESSURE_PAYLOAD`)  
- AgentDojo-style adaptive eval → nightly trend, not pass/fail safety  
- Covert channel: known encodings + **capacity** as durable control  
- SMCP / attestation: test advisory **and** require polarities  
- OWASP MCP Top 10 / ASI06 memory: fixture suites; OOB path via capability-reduction / OS sandbox elsewhere  

Bibliography IDs and longer survey content live in the Bastion companion; keep the two in sync from one editorial source to avoid drift. This file stays **evaluation- and suite-weighted**.

---

## 8. Implementation checklist (follow-up PRs)

When implementing Chosen items:

1. Recorded-verdict / fixture server under test only  
2. Preserve `fail_under = 100`  
3. Wire OWASP (and later AISVS/ATLAS/ASI) metadata into SARIF  
4. Tag nightly work `semantic_live` / `adaptive`; never flip `proven` from those runs  
5. Update **this file** (move rows from §2 → §1) — do not create a parallel backlog doc  
6. Pair each Bastion control with a harness suite before calling the control “done”  

---

*Document version: 2026-08-16 · Product docs track 5.1.0 · Companion: Bastion `MCP-BASTION-CYBER-EXTENSIONS.md`*
