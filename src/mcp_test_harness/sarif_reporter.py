"""SARIF 3.0.1 export for security-tagged test failures (GitHub Code Scanning)."""

from __future__ import annotations

import json
from typing import Any

from mcp_test_harness import __version__
from mcp_test_harness.models import CaseResult, CaseStatus, SessionResults
from mcp_test_harness.security_rules import RULES, SecurityRule, infer_rule_for_case

_SARIF_SCHEMA = "https://json.schemastore.org/sarif-3.0.1.json"
_SEVERITY_TO_LEVEL = {
    "critical": "error",
    "high": "error",
    "medium": "warning",
    "low": "note",
    "info": "note",
}


def _sarif_level(rule: SecurityRule) -> str:
    return _SEVERITY_TO_LEVEL.get(rule.severity.lower(), "warning")


def _collect_rules(cases: list[CaseResult]) -> list[SecurityRule]:
    seen: dict[str, SecurityRule] = {}
    for tr in cases:
        rule = infer_rule_for_case(tr)
        if rule is not None:
            seen[rule.rule_id] = rule
    return list(seen.values())


def _rule_descriptor(rule: SecurityRule, index: int) -> dict[str, Any]:
    return {
        "id": rule.rule_id,
        "name": rule.name,
        "shortDescription": {"text": rule.name},
        "fullDescription": {"text": f"{rule.framework} / {rule.owasp_id}: {rule.name}"},
        "defaultConfiguration": {"level": _sarif_level(rule)},
        "helpUri": rule.help_uri,
        "properties": {
            "framework": rule.framework,
            "owasp_id": rule.owasp_id,
            "tags": ["security", rule.framework.lower()],
        },
    }


def _result_for_case(tr: CaseResult, rule_index: dict[str, int]) -> dict[str, Any] | None:
    rule = infer_rule_for_case(tr)
    if rule is None:
        return None
    location_uri = (tr.file or tr.module or tr.name).replace("\\", "/")
    msg = tr.error or f"Security test {tr.name} {tr.status.value}"
    return {
        "ruleId": rule.rule_id,
        "ruleIndex": rule_index[rule.rule_id],
        "level": _sarif_level(rule),
        "message": {"text": msg},
        "locations": [
            {
                "physicalLocation": {
                    "artifactLocation": {"uri": location_uri},
                },
            },
        ],
        "properties": {
            "test_name": tr.name,
            "owasp_id": rule.owasp_id,
            "framework": rule.framework,
            "duration_ms": tr.duration_ms,
        },
    }


class SARIFReporter:
    """Emit SARIF 3.0.1 for failed security-tagged tests."""

    def generate(self, results: SessionResults) -> str:
        failed_security = [
            tr
            for tr in results.test_results
            if tr.status in (CaseStatus.FAILED, CaseStatus.ERROR, CaseStatus.TIMEOUT)
            and infer_rule_for_case(tr) is not None
        ]

        active_rules = _collect_rules(failed_security) if failed_security else list(RULES.values())[:1]
        rule_index = {r.rule_id: i for i, r in enumerate(active_rules)}
        descriptors = [_rule_descriptor(r, i) for i, r in enumerate(active_rules)]

        sarif_results: list[dict[str, Any]] = []
        for tr in failed_security:
            item = _result_for_case(tr, rule_index)
            if item is not None:
                sarif_results.append(item)

        doc: dict[str, Any] = {
            "version": "3.0.1",
            "$schema": _SARIF_SCHEMA,
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "mcp-test-harness",
                            "version": __version__,
                            "informationUri": "https://github.com/vaquarkhan/mcp-test-harness",
                            "rules": descriptors,
                        },
                    },
                    "results": sarif_results,
                    "invocations": [
                        {
                            "executionSuccessful": results.failed + results.errored == 0,
                            "endTimeUtc": results.finished_at,
                            "startTimeUtc": results.started_at,
                        },
                    ],
                },
            ],
        }
        return json.dumps(doc, indent=2)
