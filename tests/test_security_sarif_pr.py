"""Tests for SARIF export, OWASP rule mapping, and PR summaries."""

from __future__ import annotations

import json

from mcp_test_harness.models import CaseResult, CaseStatus, SessionResults
from mcp_test_harness.pr_summary import generate_pr_summary
from mcp_test_harness.reporting import JSONReporter
from mcp_test_harness.sarif_reporter import SARIFReporter
from mcp_test_harness.security_rules import build_security_findings, infer_rule_for_case


def _session(*cases: CaseResult) -> SessionResults:
    return SessionResults(
        test_results=list(cases),
        total_duration_ms=100.0,
        server_capabilities={},
        protocol_version="2025-03-26",
        harness_version="1.2.0",
        passed=sum(1 for c in cases if c.status == CaseStatus.PASSED),
        failed=sum(1 for c in cases if c.status == CaseStatus.FAILED),
        errored=0,
        skipped=0,
        timed_out=0,
        unified_summary={
            "gate": "fail",
            "categories": {
                "security": {
                    "total": 1,
                    "passed": 0,
                    "failed": 1,
                    "score_pct": 0.0,
                    "status": "fail",
                },
            },
            "coverage_headline": "3 tools tested, 1 untested, 0 missing auth tests",
        },
    )


def test_infer_rule_from_error_message() -> None:
    tr = CaseResult(
        name="test_injection",
        module="tests.test_sec",
        status=CaseStatus.FAILED,
        duration_ms=5.0,
        error="Tool did not block 1 injection payload(s)",
        tags=["security"],
    )
    rule = infer_rule_for_case(tr)
    assert rule is not None
    assert rule.rule_id == "mcp06-prompt-injection"
    assert rule.owasp_id == "MCP06"


def test_infer_rule_from_tag() -> None:
    tr = CaseResult(
        name="test_auth",
        module="tests.test_sec",
        status=CaseStatus.FAILED,
        duration_ms=5.0,
        error="denied",
        tags=["security", "mcp07"],
    )
    rule = infer_rule_for_case(tr)
    assert rule is not None
    assert rule.rule_id == "mcp07-insufficient-auth"


def test_non_security_case_returns_none() -> None:
    tr = CaseResult(
        name="test_ok",
        module="tests.test_func",
        status=CaseStatus.FAILED,
        duration_ms=1.0,
        error="assertion failed",
        tags=["smoke"],
    )
    assert infer_rule_for_case(tr) is None


def test_build_security_findings_and_json() -> None:
    tr = CaseResult(
        name="test_traversal",
        module="tests/test_sec.py",
        file="tests/test_sec.py",
        status=CaseStatus.FAILED,
        duration_ms=12.0,
        error="path traversal check failed",
        tags=["security"],
    )
    session = _session(tr)
    findings = build_security_findings(session)
    assert len(findings) == 1
    assert findings[0]["rule"]["id"] == "path-traversal"

    data = json.loads(JSONReporter().generate(session))
    assert "security_findings" in data
    assert data["security_findings"][0]["rule"]["owasp_id"] == "MCP05"


def test_sarif_reporter_structure() -> None:
    tr = CaseResult(
        name="test_leak",
        module="tests/test_sec.py",
        file="tests/test_sec.py",
        status=CaseStatus.FAILED,
        duration_ms=8.0,
        error="matched secret pattern(s)",
        tags=["security"],
    )
    sarif = json.loads(SARIFReporter().generate(_session(tr)))
    assert sarif["version"] == "2.4.0"
    run = sarif["runs"][0]
    assert run["tool"]["driver"]["name"] == "mcp-test-harness"
    assert len(run["results"]) == 1
    assert run["results"][0]["ruleId"] == "mcp01-token-mismanagement"
    assert run["results"][0]["properties"]["owasp_id"] == "MCP01"


def test_sarif_empty_when_no_security_failures() -> None:
    tr = CaseResult(
        name="test_ok",
        module="tests.test_func",
        status=CaseStatus.PASSED,
        duration_ms=1.0,
        tags=["security"],
    )
    sarif = json.loads(SARIFReporter().generate(_session(tr)))
    assert sarif["runs"][0]["results"] == []


def test_infer_rule_explicit_rule_tag() -> None:
    tr = CaseResult(
        name="test_x",
        module="tests.test_sec",
        status=CaseStatus.FAILED,
        duration_ms=1.0,
        error="fail",
        tags=["security", "path-traversal"],
    )
    rule = infer_rule_for_case(tr)
    assert rule is not None
    assert rule.rule_id == "path-traversal"


def test_infer_rule_owasp_prefix_tag() -> None:
    tr = CaseResult(
        name="test_x",
        module="tests.test_sec",
        status=CaseStatus.FAILED,
        duration_ms=1.0,
        error="fail",
        tags=["security", "owasp:mcp03-tool-poisoning"],
    )
    rule = infer_rule_for_case(tr)
    assert rule is not None
    assert rule.rule_id == "mcp03-tool-poisoning"


def test_infer_rule_default_for_security_without_match() -> None:
    tr = CaseResult(
        name="test_generic",
        module="tests.test_sec",
        status=CaseStatus.FAILED,
        duration_ms=1.0,
        error="something else",
        tags=["security"],
    )
    rule = infer_rule_for_case(tr)
    assert rule is not None
    assert rule.rule_id == "mcp06-prompt-injection"


def test_result_for_case_returns_none_for_non_security() -> None:
    from mcp_test_harness.sarif_reporter import _result_for_case

    tr = CaseResult(
        name="test_func",
        module="tests.test_func",
        status=CaseStatus.FAILED,
        duration_ms=1.0,
        error="assertion",
        tags=["smoke"],
    )
    assert _result_for_case(tr, {}) is None


def test_pr_summary_truncates_many_failures() -> None:
    failed = [
        CaseResult(
            name=f"test_{i}",
            module="tests/test_sec.py",
            status=CaseStatus.FAILED,
            duration_ms=1.0,
            error="fail",
            tags=["security"],
        )
        for i in range(26)
    ]
    session = SessionResults(
        test_results=failed,
        total_duration_ms=100.0,
        server_capabilities={},
        protocol_version="",
        harness_version="1.2.0",
        passed=0,
        failed=26,
        errored=0,
        skipped=0,
        timed_out=0,
    )
    md = generate_pr_summary(session)
    assert "and 1 more" in md

    from mcp_test_harness.security_rules import rule_by_id

    assert rule_by_id("missing") is None
    assert rule_by_id("mcp07-insufficient-auth") is not None


def test_pr_summary_minimal_session() -> None:
    session = SessionResults(
        test_results=[],
        total_duration_ms=0.0,
        server_capabilities={},
        protocol_version="",
        harness_version="1.2.0",
        passed=0,
        failed=0,
        errored=0,
        skipped=0,
        timed_out=0,
    )
    md = generate_pr_summary(session)
    assert "Overall gate" in md

    tr = CaseResult(
        name="test_injection",
        module="tests/test_sec.py",
        file="tests/test_sec.py",
        status=CaseStatus.FAILED,
        duration_ms=5.0,
        error="injection payload echoed",
        tags=["security"],
    )
    md = generate_pr_summary(_session(tr))
    assert "## MCP Test Harness" in md
    assert "Security" in md
    assert "test_injection" in md
    assert "Coverage:" in md
