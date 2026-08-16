# MCP Test Harness — Cyber-Security Suites and Backlog (Consolidated)

**Single source** for harness cyber-security work. Companion (runtime): Bastion `MCP-BASTION-CYBER-EXTENSIONS.md`. **No third file.**

**Honest framing:** green means the encoded corpus is caught *reproducibly* in CI — not safety against a novel adaptive adversary, and not live compliance.

## Nature (unchanged)

Python ≥3.10, `src/mcp_test_harness/`, hatchling, pytest asyncio auto, `fail_under=100`, gated path has **no live-model dependency**. Gated = recorded-verdict/fixtures; `semantic_live` / `adaptive` = nightly reported only.

## 1. Implemented (shipped)

| Capability | Module / entry |
|------------|----------------|
| Suite A semantic egress | `security_payloads.py` |
| Suite B known encodings + capacity/media | `security_payloads.py`, `suite_b_capacity.py` |
| Suite C attestation polarities | `attestation.py` |
| Suite D quarantine / eviction / cross-tenant | `suite_d.py` |
| Incident E–K | `incident_conformance.py` |
| Audit-chain verifier | `audit_chain.py`, `mcp-test audit verify` |
| Load resilience (deny-codes, control engage, no-fail-open, fairness, SLO) | `load_resilience.py` (+ existing `assert_throughput` / `assert_load_phases`) |
| Schema RCE-precondition rules | `schema_rules.py` |
| Confused-deputy / scope / pre-tool-hook | `authz_conformance.py` |
| Assurance evidence / metrics / OSCAL assessment-results | `evidence.py`, `metrics.py`, `oscal.py` |
| Trust-boundary + launch-gate reports | `assurance_reports.py` |
| Adaptive trend (nightly helpers) | `adaptive.py` |
| Numbat fixture ingestion contract | `endpoint_evidence.py`, `tests/fixtures/numbat_findings.ndjson` |
| AGENTS.md hidden-Unicode | `agents_md_scan.py` |
| OWASP + AISVS/ATLAS/ASI tags | `security_rules.py` |
| Markers / nightly workflow | `pyproject.toml`, `security-nightly.yml` |

## 2. Deferred (not next)

Package hallucination corpus · external scanner aggregation as a **gate** · Hub community marketplace · recommendation-poisoning after more Bastion pairing.

## 3. Rejected (do not build)

Live third-party offense · adaptive as PR gate · live Numbat/OS hooks · IFC/A2A as proven · OSCAL catalog authorship · red-team consoles.

## 4. Usage (quick)

```bash
mcp-test audit verify chain.json
mcp-test scan-agents
```

```python
from mcp_test_harness import (
    assert_audit_chain_intact,
    assert_capacity_enforced,
    assert_control_engages_under_load,
    assert_schema_preconditions_clean,
    assert_untrusted_context_quarantined,
)
```

Nightly only: `run_adaptive_trend`, `assert_detection_rate` under `@marker(tags=["adaptive"])` / `semantic_live`.

*Document version: 2026-08-16 · Product 5.2.0*
