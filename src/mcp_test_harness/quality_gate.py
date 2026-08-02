"""Declarative MCP quality-gate evaluation (CI-native, opt-in policy).

Complements existing pass/fail exit codes and SARIF/HTML reports without
introducing a hosted dashboard or history store.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mcp_test_harness.models import CaseResult, SessionResults
from mcp_test_harness.security_rules import RULES, build_security_findings

_SEVERITY_RANK: dict[str, int] = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}

_SECURITY_TAGS = frozenset({"security", "sec"})
_VALID_SEVERITIES = frozenset(_SEVERITY_RANK)


@dataclass(frozen=True)
class QualityGatePolicy:
    """Opt-in quality-gate knobs from ``quality_gate:`` in mcp-test.yaml."""

    require_security_tests: bool = False
    fail_on_severity: str | None = None  # low|medium|high|critical


def parse_quality_gate_policy(raw: dict[str, Any] | None) -> QualityGatePolicy:
    """Build a :class:`QualityGatePolicy` from a config mapping."""
    data = raw or {}
    sev = data.get("fail_on_severity")
    if sev is not None:
        sev_norm = str(sev).strip().lower()
        if sev_norm not in _VALID_SEVERITIES:
            raise ValueError(
                f"quality_gate.fail_on_severity must be one of "
                f"{sorted(_VALID_SEVERITIES)}, got {sev!r}"
            )
        sev = sev_norm
    return QualityGatePolicy(
        require_security_tests=bool(data.get("require_security_tests", False)),
        fail_on_severity=sev,
    )


def _security_tagged_cases(results: SessionResults) -> list[CaseResult]:
    out: list[CaseResult] = []
    for tr in results.test_results:
        tags = {t.lower() for t in tr.tags}
        if tags & _SECURITY_TAGS:
            out.append(tr)
    return out


def evaluate_quality_gate(
    results: SessionResults,
    policy: QualityGatePolicy | None = None,
) -> dict[str, Any]:
    """Evaluate the quality gate and return a JSON-serialisable result."""
    pol = policy or QualityGatePolicy()
    findings = build_security_findings(results)
    reasons: list[str] = []

    overall_failed = results.failed + results.errored + results.timed_out
    overall_total = len(results.test_results)
    status = (
        "pass"
        if overall_total and overall_failed == 0
        else ("fail" if overall_failed else "n/a")
    )
    if overall_failed:
        reasons.append(f"{overall_failed} test failure(s)")

    sec_cases = _security_tagged_cases(results)
    if pol.require_security_tests and not sec_cases:
        status = "fail"
        reasons.append("require_security_tests: no security-tagged tests ran")

    if pol.fail_on_severity and findings:
        threshold = _SEVERITY_RANK[pol.fail_on_severity]
        bad = [
            f
            for f in findings
            if _SEVERITY_RANK.get(str(f.get("rule", {}).get("severity", "")).lower(), 0)
            >= threshold
        ]
        if bad:
            status = "fail"
            reasons.append(
                f"{len(bad)} security finding(s) at or above severity "
                f"{pol.fail_on_severity}"
            )

    by_severity: dict[str, int] = {}
    for finding in findings:
        sev = str(finding.get("rule", {}).get("severity", "unknown")).lower()
        by_severity[sev] = by_severity.get(sev, 0) + 1

    return {
        "status": status,
        "reasons": reasons,
        "policy": {
            "require_security_tests": pol.require_security_tests,
            "fail_on_severity": pol.fail_on_severity,
        },
        "security_findings": {
            "total": len(findings),
            "by_severity": by_severity,
        },
        "rules_catalog_size": len(RULES),
        "security_tests_ran": len(sec_cases),
    }


def apply_quality_gate(
    results: SessionResults,
    policy: QualityGatePolicy | None = None,
) -> dict[str, Any]:
    """Attach ``unified_summary.quality_gate`` and align legacy ``gate``."""
    from mcp_test_harness.unified_report import build_unified_summary

    us = dict(results.unified_summary or build_unified_summary(results))
    qg = evaluate_quality_gate(results, policy)
    us["quality_gate"] = qg
    if qg["status"] == "fail":
        us["gate"] = "fail"
    elif us.get("gate") in (None, "n/a") and qg["status"] != "n/a":
        us["gate"] = qg["status"]
    results.unified_summary = us
    return qg
