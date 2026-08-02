"""Tests for opt-in CRA Annex I conformity matrix reporter."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_test_harness.cli import _run_harness
from mcp_test_harness.config import HarnessConfig, load_config
from mcp_test_harness.cra_reporter import CRATechnicalDocumentReporter, _normalize_tags
from mcp_test_harness.models import CaseResult, CaseStatus, SessionResults


def _session(*cases: CaseResult) -> SessionResults:
    return SessionResults(
        test_results=list(cases),
        total_duration_ms=50.0,
        server_capabilities={},
        protocol_version="2025-03-26",
        harness_version="4.0.0",
        passed=sum(1 for c in cases if c.status == CaseStatus.PASSED),
        failed=sum(1 for c in cases if c.status == CaseStatus.FAILED),
        errored=0,
        skipped=0,
        timed_out=0,
    )


def test_normalize_tags_chaos_shorthand() -> None:
    assert "chaos" in _normalize_tags(["chaos:truncate", "Security"])
    assert "security" in _normalize_tags(["chaos:truncate", "Security"])
    assert _normalize_tags(["", "  "]) == set()
    assert _normalize_tags(None) == set()


def test_cra_matrix_maps_security_and_chaos() -> None:
    results = _session(
        CaseResult(
            name="test_injection",
            module="t",
            status=CaseStatus.PASSED,
            duration_ms=1.0,
            tags=["security"],
        ),
        CaseResult(
            name="test_delay",
            module="t",
            status=CaseStatus.PASSED,
            duration_ms=1.0,
            tags=["chaos:delay_ms:10"],
        ),
        CaseResult(
            name="test_latency",
            module="t",
            status=CaseStatus.FAILED,
            duration_ms=1.0,
            error="slow",
            tags=["perf"],
        ),
        CaseResult(
            name="test_echo",
            module="t",
            status=CaseStatus.PASSED,
            duration_ms=1.0,
            tags=["smoke"],
        ),
    )
    doc = json.loads(CRATechnicalDocumentReporter().generate(results))
    assert doc["schema"] == "mcp-test-harness.cra_conformity_matrix.v1"
    assert "EU 2024/2847" in doc["regulation"]
    assert "not legal advice" in doc["disclaimer"].lower()
    by_id = {row["cra_article"]: row for row in doc["matrix"]}
    assert by_id["annex-i-vulnerability-handling"]["status"] == "pass"
    assert by_id["annex-i-resilience"]["status"] == "pass"
    assert by_id["annex-i-availability"]["status"] == "fail"
    assert "test_latency" in by_id["annex-i-availability"]["tests_failed"]
    assert by_id["annex-i-integrity"]["status"] == "pass"
    assert doc["summary"]["themes_total"] == 5


def test_cra_matrix_no_evidence_when_untagged() -> None:
    results = _session(
        CaseResult(
            name="test_plain",
            module="t",
            status=CaseStatus.PASSED,
            duration_ms=1.0,
            tags=[],
        ),
    )
    doc = json.loads(CRATechnicalDocumentReporter().generate(results))
    assert all(row["status"] == "no_evidence" for row in doc["matrix"])
    assert doc["summary"]["themes_without_matching_tests"] == 5


def test_config_cra_output_from_yaml(tmp_path: Path) -> None:
    from argparse import Namespace

    cfg = tmp_path / "mcp-test.yaml"
    cfg.write_text(
        "server:\n  command: python -m demo\n"
        "report:\n  cra_output: reports/cra.json\n",
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
        pdf_output=None,
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
    assert loaded.cra_output == "reports/cra.json"


@pytest.mark.asyncio
async def test_cli_writes_cra_output(tmp_path: Path) -> None:
    from mcp_test_harness.discovery import HarnessCase, HarnessModule

    out = tmp_path / "cra.json"
    config = HarnessConfig(
        server_command="python -m demo",
        cra_output=str(out),
        schema_validation=False,
    )

    async def _f() -> None:
        return

    tc = HarnessCase(name="t", module_path=Path("m.py"), func=_f, markers={}, is_async=True)
    hmod = HarnessModule(path=Path("m.py"), test_cases=[tc])
    empty = SessionResults(
        test_results=[
            CaseResult("t", "m.py", CaseStatus.PASSED, 1.0, tags=["security"]),
        ],
        total_duration_ms=1.0,
        server_capabilities={},
        protocol_version="2025-03-26",
        harness_version="4.0.0",
        passed=1,
        failed=0,
        errored=0,
        skipped=0,
        timed_out=0,
    )
    with (
        patch("mcp_test_harness.cli.discover_tests", return_value=[hmod]),
        patch("mcp_test_harness.scheduler.HarnessScheduler") as hs,
        patch("mcp_test_harness.plugins.PluginRegistry") as preg,
    ):
        preg.return_value.discover_and_load = MagicMock()
        preg.return_value.expose_assertions = MagicMock()
        preg.return_value.apply_discovery_hooks = MagicMock(side_effect=lambda m: m)
        hs.return_value.run_sequential = AsyncMock(return_value=empty)
        code = await _run_harness(config, list_only=False)
    assert code == 0
    assert out.is_file()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["schema"] == "mcp-test-harness.cra_conformity_matrix.v1"
