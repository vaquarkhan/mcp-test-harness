"""Build resiliency experiment scorecards from run results."""

from __future__ import annotations

from typing import Any

from mcp_test_harness.experiments.models import ExperimentTemplate
from mcp_test_harness.experiments.stop_conditions import evaluate_stop_condition
from mcp_test_harness.models import CaseResult, CaseStatus, SessionResults

_GRADE_THRESHOLDS: tuple[tuple[float, str], ...] = (
    (90.0, "A"),
    (75.0, "B"),
    (60.0, "C"),
    (40.0, "D"),
    (0.0, "F"),
)


def _grade_for_score(score_pct: float | None) -> str:
    if score_pct is None:
        return "n/a"
    for threshold, letter in _GRADE_THRESHOLDS:
        if score_pct >= threshold:
            return letter
    return "F"  # only when score_pct < 0


def _experiment_id_from_result(result: CaseResult) -> str | None:
    for tag in result.tags:
        if tag.startswith("experiment:"):
            return tag.split(":", 1)[1]
    return None


def _status_label(result: CaseResult, aborted: bool) -> str:
    if aborted:
        return "aborted"
    if result.status == CaseStatus.SKIPPED:
        return "skipped"
    if result.status == CaseStatus.PASSED:
        return "passed"
    return "failed"


def build_experiment_scorecard(
    results: SessionResults,
    templates: dict[str, ExperimentTemplate],
    *,
    aborted_reasons: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build scorecard dict from session results and catalog metadata."""
    reasons = aborted_reasons or {}
    by_id: dict[str, CaseResult] = {}
    for tr in results.test_results:
        exp_id = _experiment_id_from_result(tr)
        if exp_id:
            by_id[exp_id] = tr

    entries: list[dict[str, Any]] = []
    passed = failed = skipped = aborted = 0

    for exp_id in sorted(templates.keys()):
        template = templates[exp_id]
        tr = by_id.get(exp_id)
        if tr is None:
            entries.append(
                {
                    "id": exp_id,
                    "title": template.title,
                    "hypothesis": template.hypothesis,
                    "status": "missing",
                    "aborted": False,
                    "catalog_status": template.status,
                },
            )
            continue

        is_aborted = exp_id in reasons
        label = _status_label(tr, is_aborted)
        if label == "passed":
            passed += 1
        elif label == "failed":
            failed += 1
        elif label == "skipped":
            skipped += 1
        elif label == "aborted":
            aborted += 1

        entry: dict[str, Any] = {
            "id": exp_id,
            "title": template.title,
            "hypothesis": template.hypothesis,
            "status": label,
            "aborted": is_aborted,
            "catalog_status": template.status,
            "duration_ms": tr.duration_ms,
        }
        if is_aborted:
            entry["abort_reason"] = reasons[exp_id]
        if tr.error and label in ("failed", "aborted"):
            entry["error"] = tr.error
        entries.append(entry)

    scored_total = passed + failed + aborted
    score_pct = round(100.0 * passed / scored_total, 1) if scored_total else None

    return {
        "grade": _grade_for_score(score_pct),
        "score_pct": score_pct,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "aborted": aborted,
        "total": len(entries),
        "experiments": entries,
    }


def collect_abort_reasons(
    results: SessionResults,
    templates: dict[str, ExperimentTemplate],
) -> dict[str, str]:
    """Evaluate stop conditions for each experiment result."""
    reasons: dict[str, str] = {}
    for tr in results.test_results:
        exp_id = _experiment_id_from_result(tr)
        if not exp_id or exp_id not in templates:
            continue
        aborted, reason = evaluate_stop_condition(templates[exp_id], tr)
        if aborted and reason:
            reasons[exp_id] = reason
    return reasons


def scorecard_from_report(report: dict[str, Any]) -> dict[str, Any] | None:
    """Extract experiment scorecard from a JSON report dict."""
    us = report.get("unified_summary") or {}
    exp = us.get("experiments")
    return exp if isinstance(exp, dict) else None
