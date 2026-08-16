"""Pure assurance metrics (coverage-gated helpers)."""

from __future__ import annotations

from typing import Any, Sequence

from mcp_test_harness.evidence import ControlEffectivenessRecord, CoverageMatrixEntry


def control_effectiveness(
    records: Sequence[ControlEffectivenessRecord],
) -> dict[str, Any]:
    by: dict[str, str] = {}
    for r in records:
        prev = by.get(r.control_id)
        rank = {"proven": 2, "not_proven": 1, "not_tested": 0}
        if prev is None or rank[r.outcome] > rank.get(prev, -1):
            by[r.control_id] = r.outcome
    proven = sum(1 for v in by.values() if v == "proven")
    return {
        "controls": by,
        "proven": proven,
        "total": len(by),
        "rate": (proven / len(by)) if by else 0.0,
    }


def owasp_coverage(
    records: Sequence[ControlEffectivenessRecord],
    matrix: Sequence[CoverageMatrixEntry],
) -> dict[str, Any]:
    items: dict[str, dict[str, Any]] = {}
    for e in matrix:
        for oid in e.owasp_items:
            items.setdefault(
                oid,
                {"in_scope": e.in_scope, "controls": [], "proven": False, "reason": e.reason},
            )
            items[oid]["controls"].append(e.control_id)
            if not e.in_scope:
                items[oid]["in_scope"] = False
                items[oid]["reason"] = e.reason
    proven_controls = {
        r.control_id for r in records if r.outcome == "proven"
    }
    for oid, row in items.items():
        if row["in_scope"] and any(c in proven_controls for c in row["controls"]):
            row["proven"] = True
    return {"items": items}


def suite_pass_rate(records: Sequence[ControlEffectivenessRecord]) -> dict[str, Any]:
    by_suite: dict[str, dict[str, int]] = {}
    for r in records:
        slot = by_suite.setdefault(r.suite, {"passed": 0, "failed": 0, "skipped": 0})
        slot["passed"] += r.passed
        slot["failed"] += r.failed
        slot["skipped"] += r.skipped
    out: dict[str, Any] = {}
    for suite, c in by_suite.items():
        total = c["passed"] + c["failed"]
        out[suite] = {
            **c,
            "pass_rate": (c["passed"] / total) if total else 0.0,
        }
    return out


def adaptive_success_rate(*, attacks: int, successes: int) -> float:
    if attacks <= 0:
        return 0.0
    return successes / attacks


def detection_rate(*, attacks: int, detected: int) -> float:
    if attacks <= 0:
        return 0.0
    return detected / attacks


def false_positive_rate(*, benign: int, flagged: int) -> float:
    if benign <= 0:
        return 0.0
    return flagged / benign
