"""OWASP MCP and general-security rule metadata for harness findings.

Rule IDs align with the mcp-shark ``owasp-mcp-2026`` and ``general-security`` packs
so SARIF and JSON reports can be correlated with static config scans.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from mcp_test_harness.models import CaseResult, CaseStatus, SessionResults

# ---------------------------------------------------------------------------
# Rule catalogue (subset exercised by harness assertions)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SecurityRule:
    """Metadata for a single security rule referenced in reports."""

    rule_id: str
    name: str
    framework: str
    owasp_id: str
    severity: str
    help_uri: str = "https://owasp.org/www-project-top-10-for-large-language-model-applications/"


RULES: dict[str, SecurityRule] = {
    "mcp06-prompt-injection": SecurityRule(
        rule_id="mcp06-prompt-injection",
        name="Prompt Injection Detection",
        framework="OWASP-MCP",
        owasp_id="MCP06",
        severity="high",
    ),
    "path-traversal": SecurityRule(
        rule_id="path-traversal",
        name="Path Traversal Detection",
        framework="general-security",
        owasp_id="MCP05",
        severity="high",
    ),
    "mcp01-token-mismanagement": SecurityRule(
        rule_id="mcp01-token-mismanagement",
        name="Token Mismanagement & Secret Exposure",
        framework="OWASP-MCP",
        owasp_id="MCP01",
        severity="high",
    ),
    "sensitive-data-exposure": SecurityRule(
        rule_id="sensitive-data-exposure",
        name="Sensitive Data Exposure",
        framework="general-security",
        owasp_id="MCP01",
        severity="high",
    ),
    "mcp07-insufficient-auth": SecurityRule(
        rule_id="mcp07-insufficient-auth",
        name="Insufficient Authentication Detection",
        framework="OWASP-MCP",
        owasp_id="MCP07",
        severity="high",
    ),
    "mcp03-tool-poisoning": SecurityRule(
        rule_id="mcp03-tool-poisoning",
        name="Tool Poisoning Detection",
        framework="OWASP-MCP",
        owasp_id="MCP03",
        severity="high",
    ),
}

_TAG_TO_RULE: dict[str, str] = {
    "mcp01": "mcp01-token-mismanagement",
    "mcp06": "mcp06-prompt-injection",
    "mcp07": "mcp07-insufficient-auth",
    "mcp03": "mcp03-tool-poisoning",
    "injection": "mcp06-prompt-injection",
    "traversal": "path-traversal",
    "secret-leak": "mcp01-token-mismanagement",
    "auth": "mcp07-insufficient-auth",
}

_ERROR_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"injection payload", re.I), "mcp06-prompt-injection"),
    (re.compile(r"path traversal", re.I), "path-traversal"),
    (re.compile(r"secret pattern", re.I), "mcp01-token-mismanagement"),
    (re.compile(r"authorization boundary|tool_denied|tool denied", re.I), "mcp07-insufficient-auth"),
    (re.compile(r"tool poisoning|poisoned", re.I), "mcp03-tool-poisoning"),
)

_SECURITY_TAGS = frozenset({"security", "sec"})


def rule_by_id(rule_id: str) -> SecurityRule | None:
    return RULES.get(rule_id)


def infer_rule_for_case(tr: CaseResult) -> SecurityRule | None:
    """Infer the best-matching security rule for a failed test case."""
    tags = {t.lower() for t in tr.tags}
    if not (tags & _SECURITY_TAGS):
        return None

    for tag in tr.tags:
        key = tag.lower().removeprefix("owasp:").removeprefix("rule:")
        if key in _TAG_TO_RULE:
            return RULES.get(_TAG_TO_RULE[key])
        if key in RULES:
            return RULES[key]

    haystack = " ".join(
        p for p in (tr.name, tr.error or "", tr.module or "") if p
    )
    for pattern, rule_id in _ERROR_PATTERNS:
        if pattern.search(haystack):
            return RULES.get(rule_id)

    return RULES.get("mcp06-prompt-injection")


def build_security_findings(results: SessionResults) -> list[dict[str, Any]]:
    """Build JSON-serialisable security findings with OWASP rule metadata."""
    findings: list[dict[str, Any]] = []
    for tr in results.test_results:
        if tr.status not in (CaseStatus.FAILED, CaseStatus.ERROR, CaseStatus.TIMEOUT):
            continue
        rule = infer_rule_for_case(tr)
        if rule is None:
            continue
        findings.append(
            {
                "test_name": tr.name,
                "file": tr.file or tr.module,
                "status": tr.status.value,
                "message": tr.error or tr.status.value,
                "rule": {
                    "id": rule.rule_id,
                    "name": rule.name,
                    "framework": rule.framework,
                    "owasp_id": rule.owasp_id,
                    "severity": rule.severity,
                },
            }
        )
    return findings
