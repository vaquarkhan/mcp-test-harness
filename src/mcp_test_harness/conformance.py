"""Conformance levels and scorecard (RFC-002)."""

from __future__ import annotations

from typing import Any

from mcp_test_harness.models import SessionResults

LEVEL_NAMES: dict[int, str] = {
    0: "Boot",
    1: "Protocol",
    2: "Covered",
    3: "Secure",
    4: "Resilient",
}

_LEVEL_COLORS: dict[str, str] = {
    "Boot": "lightgrey",
    "Protocol": "blue",
    "Covered": "green",
    "Secure": "brightgreen",
    "Resilient": "success",
    "None": "red",
}


def _cat_status(summary: dict[str, Any], name: str) -> str:
    cats = summary.get("categories") or {}
    return str((cats.get(name) or {}).get("status") or "n/a")


def _tools_tested(summary: dict[str, Any], coverage: dict[str, Any] | None) -> int:
    cov = coverage or summary.get("coverage") or {}
    return int((cov.get("summary") or {}).get("tools_tested") or 0)


def _experiment_ok(summary: dict[str, Any]) -> bool:
    exp = summary.get("experiments") or {}
    if not isinstance(exp, dict) or not exp:
        return False
    if int(exp.get("aborted") or 0) > 0:
        return False
    score = exp.get("score_pct")
    grade = str(exp.get("grade") or "")
    if score is None:
        return False
    return float(score) >= 80.0 and grade in ("A", "B")


def evaluate_conformance(
    *,
    boot: bool = False,
    protocol: bool = False,
    unified_summary: dict[str, Any] | None = None,
    coverage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate conformance levels from doctor flags and/or a run summary."""
    us = dict(unified_summary or {})
    reasons: list[str] = []

    gate = str(us.get("gate") or "n/a")
    overall = us.get("overall") or {}
    has_tests = int(overall.get("total") or 0) > 0

    if has_tests:
        boot = True
        if gate == "pass":
            protocol = True
        elif gate == "fail":
            reasons.append("overall gate failed")

    levels = {
        "boot": bool(boot),
        "protocol": bool(boot and protocol),
        "covered": False,
        "secure": False,
        "resilient": False,
    }

    if levels["protocol"] and has_tests and gate == "pass":
        tested = _tools_tested(us, coverage)
        if tested > 0:
            levels["covered"] = True
        else:
            reasons.append("covered: no tools_tested in coverage")
    elif levels["protocol"] and not has_tests:
        # try / doctor-only: stop at Protocol
        pass
    elif boot and not protocol:
        reasons.append("protocol: schema or handshake checks failed")
    elif not boot:
        reasons.append("boot: server did not start")

    if levels["covered"]:
        sec = _cat_status(us, "security")
        if sec == "pass":
            levels["secure"] = True
        else:
            reasons.append(f"secure: security status is {sec}")

        if _experiment_ok(us):
            levels["resilient"] = True
        else:
            exp = us.get("experiments") or {}
            if not exp:
                reasons.append("resilient: no experiment scorecard")
            else:
                reasons.append(
                    "resilient: need grade A/B, score >= 80%, zero aborted "
                    f"(got grade={exp.get('grade')}, score={exp.get('score_pct')}, "
                    f"aborted={exp.get('aborted')})",
                )

    level = 0
    for n, key in enumerate(("boot", "protocol", "covered", "secure", "resilient")):
        if levels[key]:
            level = n
        else:
            break

    name = LEVEL_NAMES.get(level, "Boot") if boot else "None"
    if not boot:
        level = -1
        name = "None"

    badge = {
        "label": "mcp-test",
        "message": name,
        "color": _LEVEL_COLORS.get(name, "lightgrey"),
        "url": badge_url(name),
        "markdown": badge_markdown(name),
    }

    return {
        "level": max(level, 0) if boot else -1,
        "name": name,
        "levels": levels,
        "reasons": reasons,
        "badge": badge,
    }


def badge_url(level_name: str) -> str:
    """Shields.io-style badge URL for README paste."""
    color = _LEVEL_COLORS.get(level_name, "lightgrey")
    msg = level_name.replace(" ", "%20")
    return f"https://img.shields.io/badge/mcp--test-{msg}-{color}"


def badge_markdown(level_name: str) -> str:
    """Markdown image for README."""
    return (
        f"[![mcp-test {level_name}]({badge_url(level_name)})]"
        f"(https://github.com/vaquarkhan/mcp-test-harness)"
    )


def conformance_from_session(results: SessionResults, *, boot: bool = True, protocol: bool = True) -> dict[str, Any]:
    """Score a completed harness session."""
    return evaluate_conformance(
        boot=boot,
        protocol=protocol,
        unified_summary=results.unified_summary or {},
        coverage=results.coverage or None,
    )


def attach_conformance(results: SessionResults, *, boot: bool = True, protocol: bool = True) -> dict[str, Any]:
    """Write conformance into ``results.unified_summary`` and return it."""
    if not results.unified_summary:
        results.unified_summary = {}
    card = conformance_from_session(results, boot=boot, protocol=protocol)
    results.unified_summary["conformance"] = card
    return card


def conformance_from_report(report: dict[str, Any]) -> dict[str, Any]:
    """Grade a JSON report dict (mcp-test JSON reporter output)."""
    us = report.get("unified_summary") if isinstance(report.get("unified_summary"), dict) else {}
    cov = report.get("coverage") if isinstance(report.get("coverage"), dict) else None
    if cov is None and isinstance(us.get("coverage"), dict):
        cov = us["coverage"]
    return evaluate_conformance(
        boot=True,
        protocol=us.get("gate") != "fail",
        unified_summary=us,
        coverage=cov,
    )
