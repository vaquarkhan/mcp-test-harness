"""Tests for declarative quality_gate evaluation and rule catalogue growth."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_test_harness.config import (
    HarnessConfig,
    _flatten_config,
    load_config,
    validate_config_file,
)
from mcp_test_harness.html_reporter import HTMLReporter
from mcp_test_harness.models import CaseResult, CaseStatus, SessionResults
from mcp_test_harness.pr_summary import generate_pr_summary
from mcp_test_harness.quality_gate import (
    QualityGatePolicy,
    apply_quality_gate,
    evaluate_quality_gate,
    parse_quality_gate_policy,
)
from mcp_test_harness.security_rules import RULES, list_rules


def _session(*cases: CaseResult) -> SessionResults:
    return SessionResults(
        test_results=list(cases),
        total_duration_ms=10.0,
        server_capabilities={},
        protocol_version="2025-03-26",
        harness_version="4.0.1",
        passed=sum(1 for c in cases if c.status == CaseStatus.PASSED),
        failed=sum(1 for c in cases if c.status == CaseStatus.FAILED),
        errored=0,
        skipped=0,
        timed_out=0,
    )


def test_rule_catalog_covers_owasp_llm_and_mcp() -> None:
    rules = list_rules()
    assert len(rules) >= 15
    ids = {r.rule_id for r in rules}
    assert "mcp06-prompt-injection" in ids
    assert "llm01-prompt-injection" in ids
    assert "llm06-excessive-agency" in ids
    assert "agent-tool-loop-abuse" in ids
    assert "mcp02-session-hijacking" in ids
    frameworks = {r.framework for r in rules}
    assert "OWASP-MCP" in frameworks
    assert "OWASP-LLM" in frameworks


def test_evaluate_pass_default_policy() -> None:
    s = _session(
        CaseResult(
            name="t",
            module="m",
            status=CaseStatus.PASSED,
            duration_ms=1.0,
            tags=["smoke"],
        )
    )
    qg = evaluate_quality_gate(s)
    assert qg["status"] == "pass"
    assert qg["rules_catalog_size"] == len(RULES)


def test_require_security_tests_fails_without_security_tags() -> None:
    s = _session(
        CaseResult(
            name="t",
            module="m",
            status=CaseStatus.PASSED,
            duration_ms=1.0,
            tags=["smoke"],
        )
    )
    qg = evaluate_quality_gate(
        s, QualityGatePolicy(require_security_tests=True)
    )
    assert qg["status"] == "fail"
    assert any("require_security_tests" in r for r in qg["reasons"])


def test_require_security_tests_passes_when_security_ran() -> None:
    s = _session(
        CaseResult(
            name="t",
            module="m",
            status=CaseStatus.PASSED,
            duration_ms=1.0,
            tags=["security", "mcp06"],
        )
    )
    qg = evaluate_quality_gate(
        s, QualityGatePolicy(require_security_tests=True)
    )
    assert qg["status"] == "pass"
    assert qg["security_tests_ran"] == 1


def test_fail_on_severity_high() -> None:
    s = _session(
        CaseResult(
            name="test_injection",
            module="m",
            status=CaseStatus.FAILED,
            duration_ms=1.0,
            error="Tool did not block 1 injection payload(s)",
            tags=["security", "mcp06"],
        )
    )
    qg = evaluate_quality_gate(s, QualityGatePolicy(fail_on_severity="high"))
    assert qg["status"] == "fail"
    assert qg["security_findings"]["total"] >= 1
    assert qg["security_findings"]["by_severity"].get("high", 0) >= 1


def test_apply_quality_gate_sets_unified_summary() -> None:
    s = _session(
        CaseResult(
            name="t",
            module="m",
            status=CaseStatus.PASSED,
            duration_ms=1.0,
            tags=["smoke"],
        )
    )
    apply_quality_gate(s, QualityGatePolicy(require_security_tests=True))
    assert s.unified_summary is not None
    assert s.unified_summary["gate"] == "fail"
    assert s.unified_summary["quality_gate"]["status"] == "fail"


def test_parse_quality_gate_policy_invalid_severity() -> None:
    with pytest.raises(ValueError, match="fail_on_severity"):
        parse_quality_gate_policy({"fail_on_severity": "ultra"})


def test_load_config_quality_gate_section(tmp_path: Path) -> None:
    cfg = tmp_path / "mcp-test.yaml"
    cfg.write_text(
        "server:\n  command: python -m server\n"
        "quality_gate:\n  require_security_tests: true\n  fail_on_severity: high\n",
        encoding="utf-8",
    )
    ns = Namespace(
        server_command=None,
        transport=None,
        config=str(cfg),
        timeout=None,
        verbose=None,
        parallel=None,
        workers=None,
        report_format=None,
        report_output=None,
        sarif_output=None,
        cra_output=None,
        pr_summary_output=None,
        update_snapshots=None,
        filter_name=None,
        filter_marker=None,
        test_path=None,
        list=None,
        watch=None,
    )
    loaded = load_config(ns)
    assert loaded.quality_gate.require_security_tests is True
    assert loaded.quality_gate.fail_on_severity == "high"


def test_flatten_rejects_bad_fail_on_severity() -> None:
    with pytest.raises(ValueError, match="fail_on_severity"):
        _flatten_config(
            {
                "server": {"command": "x"},
                "quality_gate": {"fail_on_severity": "nope"},
            }
        )


def test_validate_config_quality_gate_errors(tmp_path: Path) -> None:
    bad_type = tmp_path / "bad_type.yaml"
    bad_type.write_text(
        "server:\n  command: x\nquality_gate: true\n",
        encoding="utf-8",
    )
    errs = validate_config_file(bad_type)
    assert any("quality_gate" in e.message and "mapping" in e.message for e in errs)

    bad_key = tmp_path / "bad_key.yaml"
    bad_key.write_text(
        "server:\n  command: x\nquality_gate:\n  unknown_opt: 1\n",
        encoding="utf-8",
    )
    errs = validate_config_file(bad_key)
    assert any("Unknown key in quality_gate" in e.message for e in errs)

    bad_sev = tmp_path / "bad_sev.yaml"
    bad_sev.write_text(
        "server:\n  command: x\nquality_gate:\n  fail_on_severity: ultra\n",
        encoding="utf-8",
    )
    errs = validate_config_file(bad_sev)
    assert any("fail_on_severity" in e.message for e in errs)


def test_apply_quality_gate_sets_gate_from_n_a() -> None:
    s = _session(
        CaseResult(
            name="t",
            module="m",
            status=CaseStatus.PASSED,
            duration_ms=1.0,
            tags=["smoke"],
        )
    )
    s.unified_summary = {"gate": "n/a"}
    apply_quality_gate(s, QualityGatePolicy())
    assert s.unified_summary["gate"] == "pass"
    assert s.unified_summary["quality_gate"]["status"] == "pass"


def test_pr_summary_includes_quality_gate_reasons() -> None:
    s = _session(
        CaseResult(
            name="t",
            module="m",
            status=CaseStatus.PASSED,
            duration_ms=1.0,
            tags=["smoke"],
        )
    )
    apply_quality_gate(s, QualityGatePolicy(require_security_tests=True))
    md = generate_pr_summary(s)
    assert "Quality gate" in md
    assert "require_security_tests" in md


def test_html_quality_gate_banner_uses_unified_summary() -> None:
    s = _session(
        CaseResult(
            name="t",
            module="m",
            status=CaseStatus.PASSED,
            duration_ms=1.0,
            tags=["smoke"],
        )
    )
    apply_quality_gate(s, QualityGatePolicy(require_security_tests=True))
    html = HTMLReporter().generate(s)
    assert "QUALITY GATE: FAILED" in html
    assert "require_security_tests" in html

    s2 = _session(
        CaseResult(
            name="t",
            module="m",
            status=CaseStatus.PASSED,
            duration_ms=1.0,
            tags=["security"],
        )
    )
    apply_quality_gate(s2, QualityGatePolicy(require_security_tests=True))
    html2 = HTMLReporter().generate(s2)
    assert "QUALITY GATE: PASSED" in html2

    empty = _session()
    apply_quality_gate(empty, QualityGatePolicy())
    html3 = HTMLReporter().generate(empty)
    assert "QUALITY GATE: N/A" in html3


def test_html_falls_back_without_quality_gate_block() -> None:
    s = _session(
        CaseResult(
            name="t",
            module="m",
            status=CaseStatus.FAILED,
            duration_ms=1.0,
            error="x",
            tags=["smoke"],
        )
    )
    s.unified_summary = {"gate": "fail"}
    html = HTMLReporter().generate(s)
    assert "QUALITY GATE: FAILED" in html


@pytest.mark.asyncio
async def test_cli_exits_one_when_quality_gate_fails_without_test_failures() -> None:
    from mcp_test_harness.cli import _run_harness
    from mcp_test_harness.discovery import HarnessCase, HarnessModule

    async def _f() -> None:
        return

    s = _session(
        CaseResult(
            name="t",
            module="m.py",
            status=CaseStatus.PASSED,
            duration_ms=1.0,
            tags=["smoke"],
        )
    )
    apply_quality_gate(s, QualityGatePolicy(require_security_tests=True))
    config = HarnessConfig(
        server_command="echo",
        schema_validation=False,
        quality_gate=QualityGatePolicy(require_security_tests=True),
    )
    tc = HarnessCase(
        name="t",
        module_path=Path("m.py"),
        func=_f,
        markers={},
        is_async=True,
    )
    hmod = HarnessModule(path=Path("m.py"), test_cases=[tc])
    with (
        patch("mcp_test_harness.cli.discover_tests", return_value=[hmod]),
        patch("mcp_test_harness.scheduler.HarnessScheduler") as hs,
        patch("mcp_test_harness.plugins.PluginRegistry") as preg,
    ):
        preg.return_value.discover_and_load = MagicMock()
        preg.return_value.expose_assertions = MagicMock()
        preg.return_value.apply_discovery_hooks = MagicMock(side_effect=lambda m: m)
        hs.return_value.run_sequential = AsyncMock(return_value=s)
        code = await _run_harness(config, list_only=False)
    assert code == 1
