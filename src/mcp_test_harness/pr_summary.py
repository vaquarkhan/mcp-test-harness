"""Markdown summary for GitHub PR comments from SessionResults."""

from __future__ import annotations

from mcp_test_harness.models import CaseStatus, SessionResults


def _status_badge(status: str) -> str:
    return {"pass": "✅ pass", "fail": "❌ fail", "n/a": "— n/a"}.get(status, status)


def generate_pr_summary(results: SessionResults) -> str:
    """Build a markdown comment body for pull-request commentary."""
    lines: list[str] = [
        "## MCP Test Harness — Run Summary",
        "",
    ]

    us = results.unified_summary or {}
    gate = us.get("gate", "n/a")
    lines.append(f"**Overall gate:** {_status_badge(gate)}")
    lines.append("")

    categories = us.get("categories", {})
    if categories:
        lines.append("| Category | Status | Score | Passed | Failed |")
        lines.append("|----------|--------|-------|--------|--------|")
        for name in ("functional", "security", "performance", "resiliency"):
            cat = categories.get(name, {})
            if not cat.get("total"):
                continue
            score = cat.get("score_pct")
            score_s = f"{score}%" if score is not None else "—"
            lines.append(
                f"| {name.title()} | {_status_badge(cat.get('status', 'n/a'))} "
                f"| {score_s} | {cat.get('passed', 0)} | {cat.get('failed', 0)} |"
            )
        lines.append("")

    headline = us.get("coverage_headline")
    if headline:
        lines.append(f"**Coverage:** {headline}")
        lines.append("")

    failed = [
        tr
        for tr in results.test_results
        if tr.status in (CaseStatus.FAILED, CaseStatus.ERROR, CaseStatus.TIMEOUT)
    ]
    if failed:
        lines.append(f"<details><summary>Failed tests ({len(failed)})</summary>")
        lines.append("")
        for tr in failed[:25]:
            loc = tr.file or tr.module
            lines.append(f"- `{loc}::{tr.name}` — {tr.error or tr.status.value}")
        if len(failed) > 25:
            lines.append(f"- … and {len(failed) - 25} more")
        lines.append("")
        lines.append("</details>")
        lines.append("")

    lines.append(
        f"_{results.passed} passed, {results.failed} failed, "
        f"{results.errored} errored, {results.skipped} skipped "
        f"({results.total_duration_ms:.0f}ms total)_"
    )
    return "\n".join(lines)
