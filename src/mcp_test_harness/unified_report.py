"""Unified run summary across functional, performance, security, and resiliency."""

from __future__ import annotations

from typing import Any

from mcp_test_harness.models import CaseResult, CaseStatus, SessionResults

_CATEGORY_TAGS: dict[str, frozenset[str]] = {
    "security": frozenset({"security", "sec"}),
    "performance": frozenset({"perf", "performance", "latency", "throughput"}),
    "resiliency": frozenset({"resiliency", "resilience", "chaos"}),
}


def _category_for_case(tr: CaseResult) -> str:
    tags = {t.lower() for t in tr.tags}
    for cat, keys in _CATEGORY_TAGS.items():
        if tags & keys:
            return cat
    return "functional"


def _score_category(cases: list[CaseResult]) -> dict[str, Any]:
    if not cases:
        return {"total": 0, "passed": 0, "failed": 0, "score_pct": None, "status": "n/a"}
    passed = sum(1 for c in cases if c.status == CaseStatus.PASSED)
    failed = sum(
        1
        for c in cases
        if c.status in (CaseStatus.FAILED, CaseStatus.ERROR, CaseStatus.TIMEOUT)
    )
    total = len(cases)
    score = round(100.0 * passed / total, 1) if total else None
    status = "pass" if failed == 0 and passed > 0 else ("fail" if failed else "n/a")
    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "score_pct": score,
        "status": status,
    }


def build_unified_summary(
    results: SessionResults,
    coverage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build portal-ready summary for JSON/HTML reports."""
    by_cat: dict[str, list[CaseResult]] = {
        "functional": [],
        "performance": [],
        "security": [],
        "resiliency": [],
    }
    for tr in results.test_results:
        by_cat[_category_for_case(tr)].append(tr)

    categories = {name: _score_category(cases) for name, cases in by_cat.items()}
    overall_failed = results.failed + results.errored + results.timed_out
    overall_pass = results.passed
    overall_total = len(results.test_results)
    gate = "pass" if overall_total and overall_failed == 0 else ("fail" if overall_failed else "n/a")

    summary: dict[str, Any] = {
        "gate": gate,
        "overall": {
            "total": overall_total,
            "passed": overall_pass,
            "failed": overall_failed,
            "skipped": results.skipped,
            "duration_ms": results.total_duration_ms,
        },
        "categories": categories,
    }
    if coverage:
        summary["coverage"] = coverage
        gaps = coverage.get("gaps", {})
        summary["coverage_headline"] = (
            f"{coverage.get('summary', {}).get('tools_tested', 0)} tools tested, "
            f"{len(gaps.get('untested_tools', []))} untested, "
            f"{len(gaps.get('tools_missing_auth_tests', []))} missing auth tests"
        )
    return summary
