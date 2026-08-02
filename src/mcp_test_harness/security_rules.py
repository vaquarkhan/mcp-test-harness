"""OWASP MCP / LLM / Agentic rule metadata for harness findings.

Rule IDs align with mcp-shark packs and OWASP LLM Top 10 / MCP themes so
SARIF and JSON reports correlate with static config scans. This is a
**CI evidence catalog** for behavioral tests — not a hosted Sonar product.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from mcp_test_harness.models import CaseResult, CaseStatus, SessionResults

# ---------------------------------------------------------------------------
# Rule catalogue
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
    # --- OWASP MCP (behavioral CI) ---
    "mcp01-token-mismanagement": SecurityRule(
        rule_id="mcp01-token-mismanagement",
        name="Token Mismanagement & Secret Exposure",
        framework="OWASP-MCP",
        owasp_id="MCP01",
        severity="high",
    ),
    "mcp02-session-hijacking": SecurityRule(
        rule_id="mcp02-session-hijacking",
        name="Session Hijacking / Confused Deputy",
        framework="OWASP-MCP",
        owasp_id="MCP02",
        severity="high",
    ),
    "mcp03-tool-poisoning": SecurityRule(
        rule_id="mcp03-tool-poisoning",
        name="Tool Poisoning Detection",
        framework="OWASP-MCP",
        owasp_id="MCP03",
        severity="high",
    ),
    "mcp04-supply-chain": SecurityRule(
        rule_id="mcp04-supply-chain",
        name="Supply Chain / Untrusted Tool Packaging",
        framework="OWASP-MCP",
        owasp_id="MCP04",
        severity="medium",
    ),
    "path-traversal": SecurityRule(
        rule_id="path-traversal",
        name="Path Traversal Detection",
        framework="general-security",
        owasp_id="MCP05",
        severity="high",
    ),
    "mcp06-prompt-injection": SecurityRule(
        rule_id="mcp06-prompt-injection",
        name="Prompt Injection Detection",
        framework="OWASP-MCP",
        owasp_id="MCP06",
        severity="high",
    ),
    "mcp07-insufficient-auth": SecurityRule(
        rule_id="mcp07-insufficient-auth",
        name="Insufficient Authentication Detection",
        framework="OWASP-MCP",
        owasp_id="MCP07",
        severity="high",
    ),
    "mcp08-context-injection": SecurityRule(
        rule_id="mcp08-context-injection",
        name="Context / Resource Injection",
        framework="OWASP-MCP",
        owasp_id="MCP08",
        severity="high",
    ),
    "mcp09-overprivileged-tools": SecurityRule(
        rule_id="mcp09-overprivileged-tools",
        name="Over-Privileged Tool Surface",
        framework="OWASP-MCP",
        owasp_id="MCP09",
        severity="medium",
    ),
    "sensitive-data-exposure": SecurityRule(
        rule_id="sensitive-data-exposure",
        name="Sensitive Data Exposure",
        framework="general-security",
        owasp_id="MCP01",
        severity="high",
    ),
    # --- OWASP LLM Top 10 (agentic / model-facing CI themes) ---
    "llm01-prompt-injection": SecurityRule(
        rule_id="llm01-prompt-injection",
        name="LLM01 Prompt Injection",
        framework="OWASP-LLM",
        owasp_id="LLM01",
        severity="high",
    ),
    "llm02-insecure-output": SecurityRule(
        rule_id="llm02-insecure-output",
        name="LLM02 Insecure Output Handling",
        framework="OWASP-LLM",
        owasp_id="LLM02",
        severity="high",
    ),
    "llm06-excessive-agency": SecurityRule(
        rule_id="llm06-excessive-agency",
        name="LLM06 Excessive Agency",
        framework="OWASP-LLM",
        owasp_id="LLM06",
        severity="high",
    ),
    "llm08-vector-and-embedding-weaknesses": SecurityRule(
        rule_id="llm08-vector-and-embedding-weaknesses",
        name="LLM08 Vector and Embedding Weaknesses",
        framework="OWASP-LLM",
        owasp_id="LLM08",
        severity="medium",
    ),
    "llm10-unbounded-consumption": SecurityRule(
        rule_id="llm10-unbounded-consumption",
        name="LLM10 Unbounded Consumption",
        framework="OWASP-LLM",
        owasp_id="LLM10",
        severity="medium",
    ),
    # --- Agentic patterns ---
    "agent-tool-loop-abuse": SecurityRule(
        rule_id="agent-tool-loop-abuse",
        name="Agent Tool-Loop Abuse / Runaway Calls",
        framework="agentic-security",
        owasp_id="LLM06",
        severity="medium",
    ),
    "agent-cross-tool-exfiltration": SecurityRule(
        rule_id="agent-cross-tool-exfiltration",
        name="Cross-Tool Data Exfiltration",
        framework="agentic-security",
        owasp_id="MCP01",
        severity="high",
    ),
}

_TAG_TO_RULE: dict[str, str] = {
    "mcp01": "mcp01-token-mismanagement",
    "mcp02": "mcp02-session-hijacking",
    "mcp03": "mcp03-tool-poisoning",
    "mcp04": "mcp04-supply-chain",
    "mcp05": "path-traversal",
    "mcp06": "mcp06-prompt-injection",
    "mcp07": "mcp07-insufficient-auth",
    "mcp08": "mcp08-context-injection",
    "mcp09": "mcp09-overprivileged-tools",
    "llm01": "llm01-prompt-injection",
    "llm02": "llm02-insecure-output",
    "llm06": "llm06-excessive-agency",
    "llm08": "llm08-vector-and-embedding-weaknesses",
    "llm10": "llm10-unbounded-consumption",
    "injection": "mcp06-prompt-injection",
    "traversal": "path-traversal",
    "secret-leak": "mcp01-token-mismanagement",
    "auth": "mcp07-insufficient-auth",
    "agency": "llm06-excessive-agency",
    "exfiltration": "agent-cross-tool-exfiltration",
    "tool-loop": "agent-tool-loop-abuse",
}

_ERROR_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"injection payload", re.I), "mcp06-prompt-injection"),
    (re.compile(r"path traversal", re.I), "path-traversal"),
    (re.compile(r"secret pattern", re.I), "mcp01-token-mismanagement"),
    (re.compile(r"authorization boundary|tool_denied|tool denied", re.I), "mcp07-insufficient-auth"),
    (re.compile(r"tool poisoning|poisoned", re.I), "mcp03-tool-poisoning"),
    (re.compile(r"session hijack|confused deputy", re.I), "mcp02-session-hijacking"),
    (re.compile(r"excessive agency|over.?privileged", re.I), "llm06-excessive-agency"),
    (re.compile(r"exfiltrat", re.I), "agent-cross-tool-exfiltration"),
    (re.compile(r"tool.?loop|runaway", re.I), "agent-tool-loop-abuse"),
)

_SECURITY_TAGS = frozenset({"security", "sec"})


def rule_by_id(rule_id: str) -> SecurityRule | None:
    return RULES.get(rule_id)


def list_rules() -> list[SecurityRule]:
    """Return all catalogue rules sorted by rule_id."""
    return [RULES[k] for k in sorted(RULES)]


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
