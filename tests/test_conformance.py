"""Tests for RFC-002 conformance levels and mcp-test try / conformance CLI."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from mcp_test_harness.conformance import (
    attach_conformance,
    badge_markdown,
    badge_url,
    conformance_from_report,
    conformance_from_session,
    evaluate_conformance,
)
from mcp_test_harness.models import CaseResult, CaseStatus, SessionResults
from mcp_test_harness.cli import main
from mcp_test_harness.try_cli import run_conformance, run_try
from mcp_test_harness.pr_summary import generate_pr_summary
from mcp_test_harness.html_reporter import HTMLReporter


def _session(
    *,
    passed: int = 1,
    failed: int = 0,
    tags: list[str] | None = None,
    tools_tested: int = 1,
    security_status: str = "n/a",
    experiments: dict | None = None,
) -> SessionResults:
    status = CaseStatus.PASSED if failed == 0 else CaseStatus.FAILED
    tr = CaseResult(
        name="t",
        module="m",
        status=status,
        duration_ms=1.0,
        tags=tags or ["smoke"],
    )
    results = SessionResults(
        test_results=[tr],
        total_duration_ms=1.0,
        server_capabilities={},
        protocol_version="",
        harness_version="2.3.0",
        passed=passed,
        failed=failed,
        coverage={"summary": {"tools_tested": tools_tested}, "gaps": {}},
    )
    from mcp_test_harness.unified_report import build_unified_summary

    results.unified_summary = build_unified_summary(results, results.coverage)
    if security_status != "n/a":
        results.unified_summary["categories"]["security"] = {
            "total": 1,
            "passed": 1 if security_status == "pass" else 0,
            "failed": 0 if security_status == "pass" else 1,
            "score_pct": 100.0 if security_status == "pass" else 0.0,
            "status": security_status,
        }
    if experiments is not None:
        results.unified_summary["experiments"] = experiments
    return results


def test_boot_only() -> None:
    card = evaluate_conformance(boot=True, protocol=False)
    assert card["name"] == "Boot"
    assert card["levels"]["boot"] is True
    assert card["levels"]["protocol"] is False


def test_protocol_from_try() -> None:
    card = evaluate_conformance(boot=True, protocol=True)
    assert card["name"] == "Protocol"
    assert card["levels"]["covered"] is False


def test_covered_level() -> None:
    results = _session(tools_tested=2)
    card = conformance_from_session(results)
    assert card["name"] == "Covered"
    assert card["levels"]["covered"] is True
    assert card["levels"]["secure"] is False


def test_secure_and_resilient() -> None:
    results = _session(
        tools_tested=1,
        security_status="pass",
        experiments={"grade": "A", "score_pct": 95.0, "aborted": 0},
    )
    card = attach_conformance(results)
    assert results.unified_summary["conformance"]["name"] == "Resilient"
    assert card["levels"]["secure"] is True
    assert card["levels"]["resilient"] is True


def test_resilient_blocked_by_abort() -> None:
    results = _session(
        tools_tested=1,
        security_status="pass",
        experiments={"grade": "A", "score_pct": 100.0, "aborted": 1},
    )
    card = conformance_from_session(results)
    assert card["levels"]["resilient"] is False
    assert any("aborted" in r for r in card["reasons"])


def test_failed_boot() -> None:
    card = evaluate_conformance(boot=False, protocol=False)
    assert card["name"] == "None"
    assert card["level"] == -1


def test_badge_helpers() -> None:
    assert "Covered" in badge_url("Covered")
    assert "shields.io" in badge_url("Covered")
    assert "mcp-test Covered" in badge_markdown("Covered")


def test_conformance_from_report(tmp_path: Path) -> None:
    results = _session(tools_tested=1)
    attach_conformance(results)
    from mcp_test_harness.reporting import JSONReporter

    text = JSONReporter().generate(results)
    data = json.loads(text)
    card = conformance_from_report(data)
    assert card["name"] == "Covered"


def test_pr_summary_includes_conformance() -> None:
    results = _session(tools_tested=1)
    attach_conformance(results)
    md = generate_pr_summary(results)
    assert "Conformance:" in md
    assert "Covered" in md


def test_html_conformance_panel() -> None:
    results = _session(tools_tested=1)
    attach_conformance(results)
    html = HTMLReporter().generate(results)
    assert "Conformance" in html
    assert "Covered" in html


def test_cli_dispatch_try_and_conformance() -> None:
    with patch("mcp_test_harness.try_cli.run_try", return_value=0) as m:
        assert main(["try", "--server-command", "echo"]) == 0
        m.assert_called_once()
    with patch("mcp_test_harness.try_cli.run_conformance", return_value=0) as m2:
        assert main(["conformance", "badge", "--level", "Covered"]) == 0
        m2.assert_called_once()


def test_conformance_badge_cli(capsys) -> None:
    assert run_conformance(["badge", "--level", "Protocol"]) == 0
    assert "Protocol" in capsys.readouterr().out


def test_conformance_grade_cli(tmp_path: Path, capsys) -> None:
    report = tmp_path / "r.json"
    results = _session(tools_tested=1)
    attach_conformance(results)
    from mcp_test_harness.reporting import JSONReporter

    report.write_text(JSONReporter().generate(results), encoding="utf-8")
    assert run_conformance(["--report", str(report)]) == 0
    assert "Covered" in capsys.readouterr().out
    assert run_conformance(["grade", "--report", str(report)]) == 0
    assert run_conformance(["--report", str(tmp_path / "missing.json")]) == 2
    assert run_conformance([]) == 2


def test_try_missing_server() -> None:
    with patch("mcp_test_harness.try_cli._discover_config_file", return_value=None):
        code = run_try([])
    assert code == 2


def test_try_protocol_ok_no_suite(tmp_path: Path) -> None:
    out = tmp_path / "out.json"
    with (
        patch("mcp_test_harness.try_cli.load_config") as load,
        patch("mcp_test_harness.try_cli._probe_boot_protocol", new_callable=AsyncMock) as probe,
        patch("mcp_test_harness.try_cli.validate_config_file", return_value=[]),
        patch("mcp_test_harness.try_cli._discover_config_file", return_value=None),
    ):
        from mcp_test_harness.config import HarnessConfig

        load.return_value = HarnessConfig(server_command="x", transport="stdio")
        probe.return_value = (True, True, None)
        assert (
            run_try(
                [
                    "--server-command",
                    "x",
                    "--report-format",
                    "json",
                    "--report-output",
                    str(out),
                ],
            )
            == 0
        )
    assert out.is_file()
    assert json.loads(out.read_text(encoding="utf-8"))["conformance"]["name"] == "Protocol"


def test_failed_gate_reason() -> None:
    results = _session(passed=0, failed=1, tools_tested=1)
    card = conformance_from_session(results)
    assert any("gate failed" in r for r in card["reasons"])


def test_experiment_score_none() -> None:
    results = _session(
        tools_tested=1,
        security_status="pass",
        experiments={"grade": "B", "score_pct": None, "aborted": 0},
    )
    card = conformance_from_session(results)
    assert card["levels"]["resilient"] is False


def test_probe_boot_protocol_paths() -> None:
    import asyncio
    from mcp_test_harness.config import HarnessConfig
    from mcp_test_harness.try_cli import _probe_boot_protocol
    from mcp_test_harness.lifecycle import StartupError

    cfg = HarnessConfig(server_command="x", transport="stdio")

    lifecycle = MagicMock()
    lifecycle.start = AsyncMock(side_effect=StartupError("nope"))
    lifecycle.shutdown = AsyncMock()
    with patch("mcp_test_harness.try_cli.ServerLifecycleManager", return_value=lifecycle):
        boot, protocol, err = asyncio.run(_probe_boot_protocol(cfg))
        assert (boot, protocol) == (False, False)
        assert err

    session = MagicMock()
    session.list_tools = AsyncMock(return_value=MagicMock(tools=[]))
    server = MagicMock(session=session, init_result=object())
    lifecycle2 = MagicMock()
    lifecycle2.start = AsyncMock(return_value=server)
    lifecycle2.shutdown = AsyncMock()
    with (
        patch("mcp_test_harness.try_cli.ServerLifecycleManager", return_value=lifecycle2),
        patch(
            "mcp_test_harness.schema.validate_mcp_server_after_connect",
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        boot, protocol, err = asyncio.run(_probe_boot_protocol(cfg))
        assert (boot, protocol, err) == (True, True, None)

    from mcp_test_harness.models import SchemaViolation

    viol = [SchemaViolation(json_path="$", expected_type="x", actual_value=None, message="bad")]
    with (
        patch("mcp_test_harness.try_cli.ServerLifecycleManager", return_value=lifecycle2),
        patch(
            "mcp_test_harness.schema.validate_mcp_server_after_connect",
            new_callable=AsyncMock,
            return_value=viol,
        ),
    ):
        boot, protocol, err = asyncio.run(_probe_boot_protocol(cfg))
        assert boot is True and protocol is False
        assert "bad" in (err or "")

    from dataclasses import replace

    cfg_ns = replace(cfg, schema_validation=False)
    with patch("mcp_test_harness.try_cli.ServerLifecycleManager", return_value=lifecycle2):
        assert asyncio.run(_probe_boot_protocol(cfg_ns))[:2] == (True, True)

def test_try_config_validation_fail(tmp_path: Path) -> None:
    cfg = tmp_path / "mcp-test.yaml"
    cfg.write_text("server:\n  command: x\n", encoding="utf-8")
    from mcp_test_harness.config import ConfigError

    with patch(
        "mcp_test_harness.try_cli.validate_config_file",
        return_value=[ConfigError("bad", line=1)],
    ):
        assert run_try(["--config", str(cfg), "--server-command", "x"]) == 2


def test_try_load_config_sysexit() -> None:
    with (
        patch("mcp_test_harness.try_cli._discover_config_file", return_value=None),
        patch("mcp_test_harness.try_cli.load_config", side_effect=SystemExit(2)),
    ):
        assert run_try(["--server-command", "x"]) == 2


def test_try_protocol_fail_exit() -> None:
    with (
        patch("mcp_test_harness.try_cli.load_config") as load,
        patch("mcp_test_harness.try_cli._probe_boot_protocol", new_callable=AsyncMock) as probe,
        patch("mcp_test_harness.try_cli.validate_config_file", return_value=[]),
        patch("mcp_test_harness.try_cli._discover_config_file", return_value=None),
    ):
        from mcp_test_harness.config import HarnessConfig

        load.return_value = HarnessConfig(server_command="x", transport="stdio")
        probe.return_value = (True, False, "schema bad")
        assert run_try(["--server-command", "x", "--no-schema"]) == 1


def test_try_unknown_suite() -> None:
    with (
        patch("mcp_test_harness.try_cli.load_config") as load,
        patch("mcp_test_harness.try_cli._probe_boot_protocol", new_callable=AsyncMock) as probe,
        patch("mcp_test_harness.try_cli.validate_config_file", return_value=[]),
        patch("mcp_test_harness.try_cli._discover_config_file", return_value=None),
    ):
        from mcp_test_harness.config import HarnessConfig

        load.return_value = HarnessConfig(server_command="x", transport="stdio")
        probe.return_value = (True, True, None)
        assert run_try(["--server-command", "x", "--suite", "no-such-suite"]) == 2


def test_try_suite_failures_exit(tmp_path: Path) -> None:
    results = _session(passed=0, failed=1, tools_tested=1)
    with (
        patch("mcp_test_harness.try_cli.load_config") as load,
        patch("mcp_test_harness.try_cli._probe_boot_protocol", new_callable=AsyncMock) as probe,
        patch("mcp_test_harness.try_cli.validate_config_file", return_value=[]),
        patch("mcp_test_harness.try_cli._discover_config_file", return_value=None),
        patch("mcp_test_harness.experiments.runner.run_experiments", new_callable=AsyncMock) as run_exp,
    ):
        from mcp_test_harness.config import HarnessConfig

        load.return_value = HarnessConfig(server_command="x", transport="stdio")
        probe.return_value = (True, True, None)
        run_exp.return_value = results
        assert run_try(["--server-command", "x", "--suite", "core"]) == 1


def test_attach_when_no_unified() -> None:
    results = SessionResults([], 0.0, {}, "", "0")
    results.unified_summary = {}
    card = attach_conformance(results, boot=True, protocol=True)
    assert card["name"] == "Protocol"
    assert results.unified_summary["conformance"]["name"] == "Protocol"


def test_conformance_from_report_empty() -> None:
    card = conformance_from_report({})
    assert card["name"] in ("Protocol", "Boot", "None")


def test_try_boot_fail() -> None:
    with (
        patch("mcp_test_harness.try_cli.load_config") as load,
        patch("mcp_test_harness.try_cli._probe_boot_protocol", new_callable=AsyncMock) as probe,
        patch("mcp_test_harness.try_cli.validate_config_file", return_value=[]),
        patch("mcp_test_harness.try_cli._discover_config_file", return_value=None),
    ):
        from mcp_test_harness.config import HarnessConfig

        load.return_value = HarnessConfig(server_command="x", transport="stdio")
        probe.return_value = (False, False, "boom")
        assert run_try(["--server-command", "x"]) == 1


def test_try_with_suite(tmp_path: Path) -> None:
    results = _session(tools_tested=1)
    attach_conformance(results)
    with (
        patch("mcp_test_harness.try_cli.load_config") as load,
        patch("mcp_test_harness.try_cli._probe_boot_protocol", new_callable=AsyncMock) as probe,
        patch("mcp_test_harness.try_cli.validate_config_file", return_value=[]),
        patch("mcp_test_harness.try_cli._discover_config_file", return_value=None),
        patch("mcp_test_harness.experiments.runner.run_experiments", new_callable=AsyncMock) as run_exp,
    ):
        from mcp_test_harness.config import HarnessConfig

        load.return_value = HarnessConfig(server_command="x", transport="stdio")
        probe.return_value = (True, True, None)
        run_exp.return_value = results
        out = tmp_path / "r.html"
        code = run_try(
            [
                "--server-command",
                "x",
                "--suite",
                "core",
                "--report-format",
                "html",
                "--report-output",
                str(out),
            ],
        )
        assert code == 0
        assert out.is_file()


def test_scheduler_attaches_conformance() -> None:
    from mcp_test_harness.scheduler import _aggregate_results

    tr = CaseResult(
        name="t",
        module="m",
        status=CaseStatus.PASSED,
        duration_ms=1.0,
        tags=["smoke"],
    )
    session = _aggregate_results(
        [tr],
        1.0,
        {},
        "1.0",
        coverage={"summary": {"tools_tested": 1}, "gaps": {}},
    )
    assert "conformance" in session.unified_summary
    assert session.unified_summary["conformance"]["name"] in (
        "Covered",
        "Protocol",
        "Boot",
        "Secure",
        "Resilient",
    )


def test_conformance_from_report_nested_coverage() -> None:
    card = conformance_from_report(
        {
            "unified_summary": {
                "gate": "pass",
                "overall": {"total": 1, "passed": 1, "failed": 0},
                "categories": {},
                "coverage": {"summary": {"tools_tested": 3}, "gaps": {}},
            },
        },
    )
    assert card["levels"]["covered"] is True


def test_try_suite_json_report(tmp_path: Path) -> None:
    results = _session(tools_tested=1)
    attach_conformance(results)
    out = tmp_path / "r.json"
    with (
        patch("mcp_test_harness.try_cli.load_config") as load,
        patch("mcp_test_harness.try_cli._probe_boot_protocol", new_callable=AsyncMock) as probe,
        patch("mcp_test_harness.try_cli.validate_config_file", return_value=[]),
        patch("mcp_test_harness.try_cli._discover_config_file", return_value=None),
        patch("mcp_test_harness.experiments.runner.run_experiments", new_callable=AsyncMock) as run_exp,
    ):
        from mcp_test_harness.config import HarnessConfig

        load.return_value = HarnessConfig(server_command="x", transport="stdio")
        probe.return_value = (True, True, None)
        run_exp.return_value = results
        assert (
            run_try(
                [
                    "--server-command",
                    "x",
                    "--suite",
                    "core",
                    "--report-format",
                    "json",
                    "--report-output",
                    str(out),
                ],
            )
            == 0
        )
    assert "unified_summary" in json.loads(out.read_text(encoding="utf-8"))


def test_covered_without_tools() -> None:
    results = _session(tools_tested=0)
    card = conformance_from_session(results)
    assert card["levels"]["covered"] is False
    assert any("tools_tested" in r for r in card["reasons"])
