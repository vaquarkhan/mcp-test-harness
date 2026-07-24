"""CRA Annex I conformity matrix reporter (opt-in evidence packaging).

Maps harness test tags to Cyber Resilience Act (Regulation EU 2024/2847)
Annex I *Security by Design* themes. Completely decoupled from core execution —
emit only when ``--cra-output`` / ``report.cra_output`` is set.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from mcp_test_harness import __version__
from mcp_test_harness.models import CaseResult, CaseStatus, SessionResults

# Tag → CRA Annex I evidence theme (minimum viable documentation mapping).
_ANNEX_I_MAP: tuple[tuple[str, str, str, tuple[str, ...]], ...] = (
    (
        "annex-i-secure-defaults",
        "Annex I — Secure by default / secure configuration",
        "Protocol schema validation, capability checks, and deterministic assertions that enforce safe defaults before tool execution.",
        ("security", "schema", "protocol"),
    ),
    (
        "annex-i-vulnerability-handling",
        "Annex I — Vulnerability handling evidence",
        "Security payload packs and OWASP MCP-tagged failures exported as machine-readable SARIF/JSON findings for CI gating.",
        ("security", "sec"),
    ),
    (
        "annex-i-resilience",
        "Annex I — Resilience against outages and attack conditions",
        "Chaos faults and resiliency experiments (RFC-005) demonstrating graceful degradation and recovery under injected failures.",
        ("chaos", "resiliency", "resilience"),
    ),
    (
        "annex-i-availability",
        "Annex I — Availability and performance under load",
        "Latency and throughput SLO gates that fail merges when agent-facing tools degrade.",
        ("perf", "performance", "latency", "throughput"),
    ),
    (
        "annex-i-integrity",
        "Annex I — Integrity of product functions",
        "Functional and regression tests (snapshots, idempotency) proving expected tool/resource behavior remains stable across releases.",
        ("functional", "regression", "snapshot", "smoke"),
    ),
)


@dataclass(frozen=True)
class _Theme:
    cra_article: str
    requirement_description: str
    detail: str
    tags: tuple[str, ...]


_THEMES = tuple(_Theme(*row) for row in _ANNEX_I_MAP)

_PASS_STATUSES = frozenset({CaseStatus.PASSED})
_FAIL_STATUSES = frozenset({CaseStatus.FAILED, CaseStatus.ERROR, CaseStatus.TIMEOUT})


def _normalize_tags(tags: list[str] | None) -> set[str]:
    out: set[str] = set()
    for t in tags or []:
        low = str(t).strip().lower()
        if not low:
            continue
        out.add(low)
        # Support chaos:truncate shorthand → chaos
        if ":" in low:
            out.add(low.split(":", 1)[0])
    return out


def _case_matches(case: CaseResult, theme_tags: tuple[str, ...]) -> bool:
    tags = _normalize_tags(case.tags)
    return any(t in tags for t in theme_tags)


def _pass_rate(executed: list[CaseResult]) -> float:
    if not executed:
        return 0.0
    passed = sum(1 for c in executed if c.status in _PASS_STATUSES)
    return round(100.0 * passed / len(executed), 2)


class CRATechnicalDocumentReporter:
    """Build a CRA conformity matrix JSON from session results (opt-in)."""

    def generate(self, results: SessionResults) -> str:
        rows: list[dict[str, Any]] = []
        for theme in _THEMES:
            executed = [c for c in results.test_results if _case_matches(c, theme.tags)]
            failed = [c for c in executed if c.status in _FAIL_STATUSES]
            rows.append(
                {
                    "cra_article": theme.cra_article,
                    "requirement_description": theme.requirement_description,
                    "detail": theme.detail,
                    "matching_tags": list(theme.tags),
                    "tests_executed": [c.name for c in executed],
                    "tests_failed": [c.name for c in failed],
                    "pass_rate": _pass_rate(executed),
                    "evidence_link": "sarif_output / report JSON / HTML dashboard from this run",
                    "status": (
                        "pass"
                        if executed and not failed
                        else ("fail" if failed else "no_evidence")
                    ),
                },
            )

        covered = sum(1 for r in rows if r["status"] == "pass")
        doc: dict[str, Any] = {
            "schema": "mcp-test-harness.cra_conformity_matrix.v1",
            "regulation": "EU 2024/2847 Cyber Resilience Act (CRA)",
            "disclaimer": (
                "Technical evidence packaging only — not legal advice, "
                "not a Notified Body conformity assessment, and not a CE mark."
            ),
            "harness_version": results.harness_version or __version__,
            "protocol_version": results.protocol_version,
            "started_at": results.started_at,
            "finished_at": results.finished_at,
            "summary": {
                "themes_total": len(rows),
                "themes_with_passing_evidence": covered,
                "themes_with_failures": sum(1 for r in rows if r["status"] == "fail"),
                "themes_without_matching_tests": sum(
                    1 for r in rows if r["status"] == "no_evidence"
                ),
            },
            "matrix": rows,
            "supply_chain": {
                "sbom": "CycloneDX bom.json attached to v* GitHub Actions release runs",
                "vulnerability_policy": ".github/SECURITY.md",
                "docs": "docs/CRA_COMPLIANCE.md",
            },
        }
        return json.dumps(doc, indent=2)
