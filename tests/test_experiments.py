"""Tests for resiliency experiment catalog (RFC-005)."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_test_harness.config import HarnessConfig
from mcp_test_harness.experiments import cli as exp_cli
from mcp_test_harness.experiments.cli import (
    _build_parser,
    _catalog_from_arg,
    _cmd_list,
    _cmd_run_async,
    _cmd_scorecard,
    _config_namespace,
    _print_scorecard,
    run_experiment_main,
)
from mcp_test_harness.experiments.compiler import (
    _tools_list,
    compile_experiment,
    compile_experiments,
)
from mcp_test_harness.experiments.loader import (
    get_experiment,
    list_experiment_ids,
    load_catalog,
    resolve_suite_members,
)
from mcp_test_harness.experiments.models import ExperimentTemplate
from mcp_test_harness.experiments.runner import resolve_experiment_ids, run_experiments, templates_for_ids
from mcp_test_harness.experiments.scorecard import (
    _experiment_id_from_result,
    _grade_for_score,
    _status_label,
    build_experiment_scorecard,
    collect_abort_reasons,
    scorecard_from_report,
)
from mcp_test_harness.experiments.stop_conditions import check_abort_trigger, evaluate_stop_condition
from mcp_test_harness.html_reporter import HTMLReporter
from mcp_test_harness.models import CaseResult, CaseStatus, SessionResults
from mcp_test_harness.cli import main


def _session_with_echo() -> MagicMock:
    session = MagicMock()
    tool = MagicMock()
    tool.name = "echo"
    tool.inputSchema = {"properties": {"text": {"type": "string"}}, "required": ["text"]}

    async def list_tools() -> MagicMock:
        resp = MagicMock()
        resp.tools = [tool]
        return resp

    session.list_tools = list_tools
    return session


def _ok_result() -> SimpleNamespace:
    return SimpleNamespace(
        isError=False,
        content=[SimpleNamespace(text="ok", isError=False)],
    )


def test_tools_list_helpers() -> None:
    assert _tools_list(MagicMock(tools=[1])) == [1]
    assert _tools_list([2]) == [2]
    assert _tools_list(MagicMock()) == []


def test_compile_and_run_latency_experiment() -> None:
    catalog = load_catalog()
    tmpl = get_experiment("latency-injection", catalog)
    case = compile_experiment(tmpl)
    assert "experiment:latency-injection" in case.markers["tags"]
    assert case.markers["chaos_faults"] == ["delay_ms:100"]

    session = _session_with_echo()
    session.call_tool = AsyncMock(return_value=_ok_result())
    asyncio.run(case.func(session))


def test_compile_gateway_503() -> None:
    tmpl = get_experiment("gateway-503")
    case = compile_experiment(tmpl)
    assert case.markers["chaos_faults"] == ["503"]
    assert "experiment:gateway-503" in case.markers["tags"]
    assert case.func.__doc__ == tmpl.hypothesis


def test_compile_partial_response() -> None:
    tmpl = get_experiment("partial-response")
    case = compile_experiment(tmpl)
    session = _session_with_echo()
    session.call_tool = AsyncMock(
        return_value=SimpleNamespace(content=[SimpleNamespace(text="truncated")]),
    )
    asyncio.run(case.func(session))


def test_compile_schema_drift() -> None:
    tmpl = get_experiment("schema-drift-handling")
    case = compile_experiment(tmpl)
    session = _session_with_echo()
    session.call_tool = AsyncMock(
        return_value=SimpleNamespace(content=[SimpleNamespace(text='{"id": 1}')]),
    )
    asyncio.run(case.func(session))


def test_compile_resiliency_assertions() -> None:
    session = _session_with_echo()
    with (
        patch("mcp_test_harness.experiments.compiler.assert_degrades_gracefully", new_callable=AsyncMock) as deg,
        patch("mcp_test_harness.experiments.compiler.assert_reconnects", new_callable=AsyncMock) as rec,
        patch("mcp_test_harness.experiments.compiler.assert_survives_crash", new_callable=AsyncMock) as crash,
    ):
        asyncio.run(compile_experiment(get_experiment("graceful-degradation")).func(session))
        asyncio.run(compile_experiment(get_experiment("reconnect-storm")).func(session))
        asyncio.run(compile_experiment(get_experiment("crash-mid-call")).func(session))
        deg.assert_awaited_once()
        rec.assert_awaited_once()
        crash.assert_awaited_once()


def test_target_tool_and_dict_tools(tmp_path: Path) -> None:
    cat_path = tmp_path / "c.yaml"
    cat_path.write_text(
        "version: 1\nsuites: {}\nexperiments:\n  t:\n"
        "    title: T\n    status: ready\n    assertion: latency_survives\n"
        "    target:\n      tool: fixed\n    timeout: 5\n",
        encoding="utf-8",
    )
    case = compile_experiment(load_catalog(cat_path).experiments["t"])
    assert case.markers["timeout"] == 5.0

    session = MagicMock()
    session.list_tools = AsyncMock(return_value=[{"name": "fixed", "inputSchema": {}}])
    session.call_tool = AsyncMock(return_value=_ok_result())
    asyncio.run(case.func(session))


def test_planned_experiment_skipped_case() -> None:
    tmpl = get_experiment("tool-hang")
    case = compile_experiment(tmpl)
    assert case.markers.get("skip") is True


def test_unknown_assertion_raises() -> None:
    tmpl = ExperimentTemplate(
        id="bad",
        title="Bad",
        hypothesis="",
        status="ready",
        assertion="not_real",
    )
    with pytest.raises(ValueError, match="Unknown assertion"):
        compile_experiment(tmpl)


def test_load_catalog_from_path(tmp_path: Path) -> None:
    cat_path = tmp_path / "cat.yaml"
    cat_path.write_text(
        "version: 2\nsuites:\n  s:\n    members: [x]\n  full:\n    members: all\n"
        "experiments:\n  x:\n    title: X\n    status: ready\n    assertion: latency_survives\n",
        encoding="utf-8",
    )
    cat = load_catalog(cat_path)
    assert cat.version == 2
    assert "x" in cat.experiments
    assert resolve_suite_members("full", cat)


def test_loader_helpers() -> None:
    ids = list_experiment_ids()
    assert "latency-injection" in ids
    assert "core" in load_catalog().suites
    members = resolve_suite_members("core")
    assert "latency-injection" in members
    with pytest.raises(KeyError):
        get_experiment("no-such-id")
    with pytest.raises(KeyError):
        resolve_suite_members("no-suite")
    assert _catalog_from_arg(None).version >= 1


def test_resolve_experiment_ids() -> None:
    assert resolve_experiment_ids(experiment_id="gateway-503") == ["gateway-503"]
    assert "latency-injection" in resolve_experiment_ids(suite="core")
    with pytest.raises(ValueError):
        resolve_experiment_ids()
    with pytest.raises(ValueError):
        resolve_experiment_ids(experiment_id="a", suite="core")


def test_stop_conditions() -> None:
    tmpl = get_experiment("latency-injection")
    tr = CaseResult(name="t", module="m", status=CaseStatus.TIMEOUT, duration_ms=1.0, error="timeout")
    assert check_abort_trigger("hang", tr)
    assert evaluate_stop_condition(tmpl, tr)[0] is True

    err_tr = CaseResult(name="t", module="m", status=CaseStatus.ERROR, duration_ms=1.0)
    assert check_abort_trigger("unhandled_exception", err_tr)

    crash_tr = CaseResult(
        name="t",
        module="m",
        status=CaseStatus.ERROR,
        duration_ms=1.0,
        error="Server crashed: boom",
    )
    assert check_abort_trigger("server_crash", crash_tr)

    leak_tr = CaseResult(
        name="t",
        module="m",
        status=CaseStatus.FAILED,
        duration_ms=1.0,
        error="leaked api_key=sk-live-abcdefghijklmnop",
    )
    assert check_abort_trigger("secret_leak", leak_tr)

    ok = CaseResult(name="t", module="m", status=CaseStatus.PASSED, duration_ms=1.0)
    assert evaluate_stop_condition(tmpl, ok) == (False, None)
    assert check_abort_trigger("bogus", ok) is None

    empty = CaseResult(name="t", module="m", status=CaseStatus.FAILED, duration_ms=1.0)
    assert check_abort_trigger("secret_leak", empty) is None


def test_scorecard_build_and_grades() -> None:
    assert _grade_for_score(None) == "n/a"
    assert _grade_for_score(95) == "A"
    assert _grade_for_score(80) == "B"
    assert _grade_for_score(65) == "C"
    assert _grade_for_score(45) == "D"
    assert _grade_for_score(10) == "F"
    assert _status_label(CaseResult("t", "m", CaseStatus.SKIPPED, 0), False) == "skipped"
    assert _status_label(CaseResult("t", "m", CaseStatus.PASSED, 0), False) == "passed"
    assert _status_label(CaseResult("t", "m", CaseStatus.FAILED, 0), True) == "aborted"
    assert _experiment_id_from_result(CaseResult("t", "m", CaseStatus.PASSED, 0, tags=["experiment:x"])) == "x"

    catalog = load_catalog()
    templates = {tid: get_experiment(tid, catalog) for tid in ["latency-injection", "gateway-503"]}
    results = SessionResults(
        test_results=[
            CaseResult(
                name="test_experiment_latency_injection",
                module="experiments/catalog/latency-injection.yaml",
                status=CaseStatus.PASSED,
                duration_ms=10.0,
                tags=["experiment", "experiment:latency-injection"],
            ),
            CaseResult(
                name="test_experiment_gateway_503",
                module="experiments/catalog/gateway-503.yaml",
                status=CaseStatus.FAILED,
                duration_ms=5.0,
                error="nope",
                tags=["experiment", "experiment:gateway-503"],
            ),
        ],
        total_duration_ms=15.0,
        server_capabilities={},
        protocol_version="",
        harness_version="0",
        passed=1,
        failed=1,
    )
    reasons = collect_abort_reasons(results, templates)
    card = build_experiment_scorecard(results, templates, aborted_reasons=reasons)
    assert card["passed"] == 1
    assert len(card["experiments"]) == 2

    skipped_tr = CaseResult(
        name="s",
        module="m",
        status=CaseStatus.SKIPPED,
        duration_ms=1.0,
        tags=["experiment:latency-injection"],
    )
    card_skip = build_experiment_scorecard(
        SessionResults([skipped_tr], 1.0, {}, "", "0"),
        {"latency-injection": templates["latency-injection"]},
    )
    assert card_skip["skipped"] == 1

    report = {"unified_summary": {"experiments": card}}
    assert scorecard_from_report(report) == card
    assert scorecard_from_report({}) is None
    assert scorecard_from_report({"unified_summary": {"experiments": []}}) is None


def test_cli_list_and_scorecard(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert _cmd_list(argparse.Namespace(suite=None, catalog=None)) == 0
    assert "latency-injection" in capsys.readouterr().out
    assert _cmd_list(argparse.Namespace(suite="core", catalog=None)) == 0
    assert "Suite: core" in capsys.readouterr().out

    report = tmp_path / "r.json"
    report.write_text(
        json.dumps(
            {
                "unified_summary": {
                    "experiments": {
                        "grade": "A",
                        "score_pct": 100.0,
                        "passed": 1,
                        "failed": 0,
                        "aborted": 0,
                        "skipped": 0,
                        "experiments": [
                            {
                                "id": "x",
                                "title": "X",
                                "status": "failed",
                                "error": "boom",
                            },
                            {
                                "id": "y",
                                "title": "Y",
                                "status": "aborted",
                                "abort_reason": "hang",
                            },
                        ],
                    },
                },
            },
        ),
        encoding="utf-8",
    )
    _print_scorecard(json.loads(report.read_text())["unified_summary"]["experiments"])
    out = capsys.readouterr().out
    assert "boom" in out
    assert "guardrail" in out

    assert run_experiment_main(["scorecard", "--report", str(report)]) == 0
    assert run_experiment_main(["scorecard", "--report", str(tmp_path / "nope.json")]) == 2
    bad = tmp_path / "bad.json"
    bad.write_text("{}", encoding="utf-8")
    assert _cmd_scorecard(argparse.Namespace(report=str(bad))) == 2


def test_cli_run_errors(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_experiment_main(["run", "no-id"]) == 2
    assert run_experiment_main(["run"]) == 2


def test_main_dispatches_experiment() -> None:
    with patch("mcp_test_harness.experiments.cli.run_experiment_main", return_value=0) as m:
        assert main(["experiment", "list"]) == 0
        m.assert_called_once_with(["list"])


def test_tool_resolution_no_tools() -> None:
    tmpl = get_experiment("latency-injection")
    case = compile_experiment(tmpl)
    session = MagicMock()
    session.list_tools = AsyncMock(return_value=MagicMock(tools=[]))
    with pytest.raises(AssertionError, match="No tools"):
        asyncio.run(case.func(session))


def test_compile_experiments_batch() -> None:
    tmpls = templates_for_ids(["gateway-503", "tool-hang"])
    cases = compile_experiments(tmpls)
    assert len(cases) == 2


def test_experiment_fault_and_stop_parsing(tmp_path: Path) -> None:
    cat_path = tmp_path / "c.yaml"
    cat_path.write_text(
        "version: 1\nsuites:\n  full:\n    members: [all]\nexperiments:\n  z:\n"
        "    title: Z\n    status: bogus\n    fault:\n      type: chaos\n      chaos_faults: [503]\n"
        "    stop_condition:\n      abort_if: [hang]\n",
        encoding="utf-8",
    )
    tmpl = load_catalog(cat_path).experiments["z"]
    assert tmpl.status == "planned"
    assert tmpl.fault.chaos_faults == ["503"]
    assert resolve_suite_members("full", load_catalog(cat_path)) == ["z"]


def test_scorecard_aborted_status() -> None:
    tmpl = get_experiment("gateway-503")
    templates = {"gateway-503": tmpl}
    tr = CaseResult(
        name="t",
        module="m",
        status=CaseStatus.PASSED,
        duration_ms=1.0,
        tags=["experiment:gateway-503"],
    )
    card = build_experiment_scorecard(
        SessionResults([tr], 1.0, {}, "", "0", passed=1),
        templates,
        aborted_reasons={"gateway-503": "secret_leak: x"},
    )
    assert card["aborted"] == 1
    assert card["experiments"][0]["status"] == "aborted"


def test_cmd_run_async_success(tmp_path: Path) -> None:
    args = argparse.Namespace(
        experiment_id="gateway-503",
        suite=None,
        catalog=None,
        config=None,
        server_command="echo ok",
        transport="stdio",
        timeout=5.0,
        verbose=False,
        report_format="json",
        report_output=str(tmp_path / "out.json"),
    )
    session = SessionResults([], 0.0, {}, "", "0")
    session.unified_summary = {"experiments": {"grade": "A", "score_pct": 100.0, "experiments": []}}
    with patch("mcp_test_harness.experiments.cli.run_experiments", new_callable=AsyncMock, return_value=session):
        assert asyncio.run(_cmd_run_async(args)) == 0
    assert (tmp_path / "out.json").is_file()


def test_cmd_run_async_failures(tmp_path: Path) -> None:
    args = argparse.Namespace(
        experiment_id=None,
        suite=None,
        catalog=None,
        config=None,
        server_command=None,
        transport=None,
        timeout=None,
        verbose=False,
        report_format="html",
        report_output=str(tmp_path / "out.html"),
    )
    assert asyncio.run(_cmd_run_async(args)) == 2

    args.experiment_id = "gateway-503"
    args.server_command = "echo"
    fail_session = SessionResults([], 0.0, {}, "", "0", failed=1)
    with patch("mcp_test_harness.experiments.cli.run_experiments", new_callable=AsyncMock, return_value=fail_session):
        assert asyncio.run(_cmd_run_async(args)) == 1

    with patch("mcp_test_harness.experiments.cli.load_config", side_effect=SystemExit(2)):
        assert asyncio.run(_cmd_run_async(args)) == 2


def test_run_experiments_integration() -> None:
    cfg = HarnessConfig(server_command="echo", transport="stdio", timeout=2.0)
    cases = compile_experiments(templates_for_ids(["tool-hang"]))
    skipped = SessionResults(
        [
            CaseResult(
                name=cases[0].name,
                module=str(cases[0].module_path),
                status=CaseStatus.SKIPPED,
                duration_ms=0.0,
                tags=cases[0].markers.get("tags", []),
            ),
        ],
        0.0,
        {},
        "",
        "0",
        skipped=1,
    )
    with patch("mcp_test_harness.experiments.runner.HarnessScheduler") as sched:
        inst = sched.return_value
        inst.run_sequential = AsyncMock(return_value=skipped)
        out = asyncio.run(run_experiments(cfg, ["tool-hang"]))
    assert "experiments" in out.unified_summary


def test_html_experiments_panel() -> None:
    results = SessionResults([], 0.0, {}, "", "0")
    results.unified_summary = {
        "experiments": {
            "grade": "B",
            "score_pct": 80.0,
            "experiments": [
                {
                    "id": "latency-injection",
                    "title": "Latency",
                    "hypothesis": "SLO holds",
                    "status": "passed",
                },
            ],
        },
    }
    html = HTMLReporter().generate(results)
    assert "Resiliency experiments" in html
    assert "latency-injection" in html
    assert HTMLReporter().generate(SessionResults([], 0.0, {}, "", "0"))


def test_config_namespace_and_parser() -> None:
    p = _build_parser()
    args = p.parse_args(["list"])
    assert args.command == "list"
    ns = _config_namespace(
        argparse.Namespace(
            config=None,
            server_command="x",
            transport="stdio",
            timeout=1.0,
            verbose=True,
            report_format="json",
            report_output="o.json",
        ),
    )
    assert ns.server_command == "x"
    with pytest.raises(SystemExit):
        run_experiment_main([])


def test_cmd_run_verbose() -> None:
    from mcp_test_harness.experiments.cli import _cmd_run

    args = argparse.Namespace(verbose=True)
    with patch("mcp_test_harness.experiments.cli.asyncio.run", return_value=0) as run:
        assert _cmd_run(args) == 0
        run.assert_called_once()


def test_catalog_from_path(tmp_path: Path) -> None:
    cat = tmp_path / "c.yaml"
    cat.write_text(
        "version: 1\nsuites: {}\nexperiments:\n  a:\n    title: A\n    status: ready\n",
        encoding="utf-8",
    )
    assert _catalog_from_arg(str(cat)).experiments["a"].title == "A"


def test_loader_skips_invalid_entries(tmp_path: Path) -> None:
    cat_path = tmp_path / "c.yaml"
    cat_path.write_text(
        "version: 1\nsuites:\n  bad: not-a-dict\nexperiments:\n  ok:\n    title: OK\n    status: ready\n    assertion: latency_survives\n  skip: string\n",
        encoding="utf-8",
    )
    cat = load_catalog(cat_path)
    assert "ok" in cat.experiments
    assert "skip" not in cat.experiments


def test_collect_abort_skips_unknown_template() -> None:
    tr = CaseResult(
        name="t",
        module="m",
        status=CaseStatus.PASSED,
        duration_ms=1.0,
        tags=["experiment:unknown"],
    )
    assert collect_abort_reasons(SessionResults([tr], 0.0, {}, "", "0"), {}) == {}


def test_compiler_coverage_gaps() -> None:
    from mcp_test_harness.chaos import ChaosFaultError
    from mcp_test_harness.experiments.compiler import (
        _gateway_503,
        _tool_name_from_session,
    )

    async def _names() -> None:
        session = MagicMock()
        session.list_tools = AsyncMock(return_value=SimpleNamespace(tools=[object()]))
        assert await _tool_name_from_session(session) == "unknown"

        session2 = MagicMock()
        session2.list_tools = AsyncMock(
            return_value=SimpleNamespace(
                tools=[{"name": "other"}, {"name": "t", "inputSchema": {}}],
            ),
        )
        session2.call_tool = AsyncMock(side_effect=ChaosFaultError("503", code=503))
        await _gateway_503(session2, get_experiment("gateway-503"))

        session3 = MagicMock()
        session3.list_tools = AsyncMock(return_value=SimpleNamespace(tools=[{"name": "t"}]))
        session3.call_tool = AsyncMock(return_value=_ok_result())
        with pytest.raises(AssertionError, match="expected simulated 503"):
            await _gateway_503(session3, get_experiment("gateway-503"))

        fixed = ExperimentTemplate(
            id="fixed",
            title="Fixed",
            hypothesis="",
            status="ready",
            assertion="latency_survives",
            target_tool="t",
        )
        session4 = MagicMock()
        session4.list_tools = AsyncMock(
            return_value=SimpleNamespace(
                tools=[
                    {"name": "other"},
                    {"name": "t", "inputSchema": {"properties": {"text": {"type": "string"}}}},
                ],
            ),
        )
        session4.call_tool = AsyncMock(return_value=_ok_result())
        await compile_experiment(fixed).func(session4)

    asyncio.run(_names())

    case = compile_experiment(get_experiment("tool-hang"))
    with pytest.raises(AssertionError, match="planned"):
        asyncio.run(case.func(MagicMock()))


def test_cli_missing_server_command() -> None:
    args = argparse.Namespace(
        experiment_id="gateway-503",
        suite=None,
        catalog=None,
        config=None,
        server_command=None,
        transport=None,
        timeout=None,
        verbose=False,
        report_format=None,
        report_output=None,
    )
    with patch("mcp_test_harness.experiments.cli._discover_config_file", return_value=None):
        assert asyncio.run(_cmd_run_async(args)) == 2


def test_scorecard_missing_and_stop_edge_cases() -> None:
    tmpl = get_experiment("latency-injection")
    card = build_experiment_scorecard(
        SessionResults([], 0.0, {}, "", "0"),
        {"latency-injection": tmpl},
    )
    assert card["experiments"][0]["status"] == "missing"
    assert _grade_for_score(0.0) == "F"
    assert _grade_for_score(-1.0) == "F"
    assert _experiment_id_from_result(CaseResult("t", "m", CaseStatus.PASSED, 0, tags=[])) is None

    tr = CaseResult(
        name="t",
        module="m",
        status=CaseStatus.FAILED,
        duration_ms=1.0,
        traceback="bearer abcdefgh123456",
    )
    assert check_abort_trigger("secret_leak", tr)


def test_collect_abort_no_reason() -> None:
    tmpl = get_experiment("latency-injection")
    with patch(
        "mcp_test_harness.experiments.scorecard.evaluate_stop_condition",
        return_value=(True, "hang: timeout"),
    ):
        tr = CaseResult(
            name="t",
            module="m",
            status=CaseStatus.PASSED,
            duration_ms=1.0,
            tags=["experiment:latency-injection"],
        )
        reasons = collect_abort_reasons(SessionResults([tr], 0.0, {}, "", "0"), {tmpl.id: tmpl})
        assert reasons["latency-injection"] == "hang: timeout"

    with patch(
        "mcp_test_harness.experiments.scorecard.evaluate_stop_condition",
        return_value=(True, None),
    ):
        assert collect_abort_reasons(SessionResults([tr], 0.0, {}, "", "0"), {tmpl.id: tmpl}) == {}


def test_cmd_list_and_scorecard_direct(tmp_path: Path) -> None:
    assert run_experiment_main(["list"]) == 0
    report = tmp_path / "r.json"
    report.write_text(
        json.dumps({"unified_summary": {"experiments": {"grade": "A", "experiments": []}}}),
        encoding="utf-8",
    )
    assert run_experiment_main(["scorecard", "--report", str(report)]) == 0


def test_cli_run_config_validation(tmp_path: Path) -> None:
    bad_cfg = tmp_path / "mcp-test.yaml"
    bad_cfg.write_text("server:\n  command: echo\n", encoding="utf-8")
    args = argparse.Namespace(
        experiment_id="gateway-503",
        suite=None,
        catalog=None,
        config=str(bad_cfg),
        server_command="echo",
        transport=None,
        timeout=None,
        verbose=False,
        report_format=None,
        report_output=None,
    )
    from mcp_test_harness.config import ConfigError

    with patch(
        "mcp_test_harness.experiments.cli.validate_config_file",
        return_value=[ConfigError("bad field", line=1)],
    ):
        assert asyncio.run(_cmd_run_async(args)) == 2


def test_run_experiment_main_run_dispatch() -> None:
    with patch("mcp_test_harness.experiments.cli._cmd_run", return_value=0) as run_cmd:
        assert run_experiment_main(["run", "gateway-503", "--server-command", "echo"]) == 0
        run_cmd.assert_called_once()


def test_run_experiment_main_unknown_command() -> None:
    with patch(
        "mcp_test_harness.experiments.cli._build_parser",
    ) as build:
        parser = build.return_value
        parser.parse_args.return_value = argparse.Namespace(command="bogus")
        with pytest.raises(AssertionError, match="unknown experiment command"):
            run_experiment_main(["bogus"])
