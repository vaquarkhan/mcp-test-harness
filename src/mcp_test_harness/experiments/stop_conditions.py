"""Evaluate experiment stop conditions (guardrails)."""

from __future__ import annotations

import re

from mcp_test_harness.experiments.models import ExperimentTemplate
from mcp_test_harness.models import CaseResult, CaseStatus
from mcp_test_harness.security_payloads import scan_text_for_secrets

_SECRET_PROBE = re.compile(
    r"(?i)(api[_-]?key|secret|password|token|bearer\s+[a-z0-9._-]{8,})",
)


def _text_for_scan(result: CaseResult) -> str:
    parts: list[str] = []
    if result.error:
        parts.append(result.error)
    if result.traceback:
        parts.append(result.traceback)
    return "\n".join(parts)


def check_abort_trigger(trigger: str, result: CaseResult) -> str | None:
    """Return a human reason if *trigger* fired for *result*, else None."""
    if trigger == "unhandled_exception" and result.status == CaseStatus.ERROR:
        return "unhandled_exception: test ended with error status"
    if trigger == "hang" and result.status == CaseStatus.TIMEOUT:
        return "hang: test exceeded timeout"
    if trigger == "server_crash":
        err = result.error or ""
        if "server crashed" in err.lower():
            return "server_crash: MCP server process exited during experiment"
    if trigger == "secret_leak":
        blob = _text_for_scan(result)
        hits = scan_text_for_secrets(blob) if blob else []
        if not hits and blob and _SECRET_PROBE.search(blob):
            hits = ["suspicious secret-like token in output"]
        if hits:
            return f"secret_leak: {hits[0]}"
    return None


def evaluate_stop_condition(
    template: ExperimentTemplate,
    result: CaseResult,
) -> tuple[bool, str | None]:
    """Return (aborted, reason) when a guardrail fired."""
    for trigger in template.stop_condition.abort_if:
        reason = check_abort_trigger(trigger, result)
        if reason:
            return True, reason
    return False, None
