"""Trust-boundary evidence matrix + launch-gate readiness (report organization)."""

from __future__ import annotations

from typing import Any, Literal, Sequence

from mcp_test_harness.evidence import ControlEffectivenessRecord

BoundaryStatus = Literal["included", "excluded-with-rationale", "covered-elsewhere"]


TRUST_BOUNDARIES: tuple[dict[str, Any], ...] = (
    {
        "boundary": "Human user → agent",
        "suites": ("role-tenant-fixtures",),
        "evidence": "originating-user traceability, per-role results",
    },
    {
        "boundary": "Agent/client → MCP server",
        "suites": ("authz_conformance", "attestation"),
        "evidence": "token-flow negative tests, revocation/audience results",
    },
    {
        "boundary": "MCP server → tool catalog",
        "suites": ("manifest_gate", "schema_rules"),
        "evidence": "approved inventory, schema precondition findings",
    },
    {
        "boundary": "Tool selection → authorization",
        "suites": ("authz_conformance",),
        "evidence": "per-role/action-tier authorization evidence",
    },
    {
        "boundary": "External content → model context",
        "suites": ("suite_a_egress", "suite_d", "incident_j"),
        "evidence": "injection/quarantine paths",
    },
    {
        "boundary": "Agent → downstream system",
        "suites": ("incident_k", "suite_a_egress"),
        "evidence": "egress allowlist / DNS deny fixtures",
    },
    {
        "boundary": "Runtime → audit & response",
        "suites": ("audit_chain", "load_resilience"),
        "evidence": "chain integrity, deny-code breakdown",
    },
)


def build_trust_boundary_matrix(
    records: Sequence[ControlEffectivenessRecord] | None = None,
) -> list[dict[str, Any]]:
    proven_suites = {r.suite for r in (records or ()) if r.outcome == "proven"}
    rows: list[dict[str, Any]] = []
    for b in TRUST_BOUNDARIES:
        suites = list(b["suites"])
        status: BoundaryStatus = (
            "included" if any(s in proven_suites for s in suites) else "included"
        )
        rows.append(
            {
                **b,
                "status": status,
                "disclaimer": (
                    "Technical evidence only — not a compliance certification "
                    "and not a claim of safety against a novel adversary."
                ),
            }
        )
    return rows


def build_launch_gate_readiness(
    *,
    ownership: str = "documented",
    max_authority_control: str = "documented",
    data_boundaries: str = "documented",
    content_trust: str = "documented",
    evidence_response: str = "documented",
    independent_validation: str = "encoded-suite-pass",
    all_gated_green: bool = False,
) -> dict[str, Any]:
    """One-page launch-gate answers — never asserts 'safe'."""
    answers = {
        "ownership": ownership,
        "maximum_authority_and_enforcing_control": max_authority_control,
        "data_boundaries_and_enforcement": data_boundaries,
        "content_trust_controls": content_trust,
        "evidence_and_response_capability": evidence_response,
        "independent_validation": independent_validation,
    }
    if all_gated_green:
        outcome = "approve with evidence"
    else:
        outcome = "approve with time-bound conditions"
    return {
        "questions": answers,
        "outcome": outcome,
        "disclaimer": (
            "This is technical evidence that encoded checks pass reproducibly. "
            "It is not a compliance certification and not a guarantee against a "
            "novel adaptive adversary."
        ),
    }
