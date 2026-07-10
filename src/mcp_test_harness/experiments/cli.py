"""`mcp-test experiment` — resiliency experiment catalog CLI."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from argparse import Namespace
from pathlib import Path

from mcp_test_harness.config import load_config, validate_config_file
from mcp_test_harness.config import _discover_config_file
from mcp_test_harness.experiments.loader import get_experiment, load_catalog
from mcp_test_harness.experiments.runner import resolve_experiment_ids, run_experiments
from mcp_test_harness.experiments.scorecard import scorecard_from_report
from mcp_test_harness.reporting import ConsoleReporter, JSONReporter

logger = logging.getLogger(__name__)


def _config_namespace(args: argparse.Namespace) -> Namespace:
    return Namespace(
        test_path="tests",
        version=False,
        list=False,
        watch=False,
        config=args.config,
        server_command=args.server_command,
        transport=args.transport,
        timeout=args.timeout,
        verbose=args.verbose,
        parallel=None,
        workers=None,
        report_format=args.report_format,
        report_output=args.report_output,
        pdf_output=None,
        sarif_output=None,
        pr_summary_output=None,
        update_snapshots=None,
        filter_name=None,
        filter_marker=None,
        fail_fast=False,
        last_failed=False,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mcp-test experiment",
        description="Run curated resiliency experiments (AWS FIS style) with guardrails and a scorecard.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    list_p = sub.add_parser("list", help="Browse the experiment catalog")
    list_p.add_argument("--suite", default=None, help="Filter to a named suite (e.g. core)")
    list_p.add_argument("--catalog", default=None, help="Path to catalog YAML (default: bundled)")

    run_p = sub.add_parser("run", help="Run one experiment or a suite")
    run_p.add_argument("experiment_id", nargs="?", default=None, help="Experiment id (e.g. crash-mid-call)")
    run_p.add_argument("--suite", default=None, help="Run a named suite instead of one id")
    run_p.add_argument("--config", default=None, help="Path to mcp-test.yaml / mcp-test.toml")
    run_p.add_argument("--server-command", dest="server_command", default=None)
    run_p.add_argument("--transport", default=None, choices=["stdio", "sse", "http"])
    run_p.add_argument("--timeout", type=float, default=None)
    run_p.add_argument("--verbose", action="store_true", default=False)
    run_p.add_argument(
        "--report-format",
        dest="report_format",
        default=None,
        choices=["json", "html"],
        help="Optional report format",
    )
    run_p.add_argument("--report-output", dest="report_output", default=None)
    run_p.add_argument("--catalog", default=None, help="Path to catalog YAML (default: bundled)")

    score_p = sub.add_parser("scorecard", help="Print resiliency grade from a JSON report")
    score_p.add_argument(
        "--report",
        required=True,
        help="Path to JSON report from `mcp-test experiment run --report-format json`",
    )

    return parser


def _catalog_from_arg(path: str | None):
    if not path:
        return load_catalog()
    return load_catalog(Path(path))


def _cmd_list(args: argparse.Namespace) -> int:
    catalog = _catalog_from_arg(args.catalog)
    ids = sorted(catalog.experiments.keys())
    if args.suite:
        from mcp_test_harness.experiments.loader import resolve_suite_members

        ids = resolve_suite_members(args.suite, catalog)
    print("Resiliency experiment catalog")
    if args.suite:
        suite = catalog.suites.get(args.suite)
        desc = suite.description if suite else ""
        print(f"  Suite: {args.suite} - {desc}")
    print()
    for exp_id in ids:
        tmpl = catalog.experiments[exp_id]
        status = tmpl.status
        print(f"  {exp_id:28} [{status:7}]  {tmpl.title}")
        if tmpl.hypothesis:
            print(f"    {tmpl.hypothesis}")
    print()
    print("Run: mcp-test experiment run <id> --server-command \"...\"")
    print("     mcp-test experiment run --suite core --server-command \"...\"")
    return 0


def _print_scorecard(scorecard: dict) -> None:
    grade = scorecard.get("grade", "n/a")
    score = scorecard.get("score_pct")
    score_txt = f"{score}%" if score is not None else "-"
    print(f"Resiliency scorecard: grade {grade} ({score_txt})")
    print(
        f"  passed={scorecard.get('passed', 0)} "
        f"failed={scorecard.get('failed', 0)} "
        f"aborted={scorecard.get('aborted', 0)} "
        f"skipped={scorecard.get('skipped', 0)}",
    )
    print()
    for entry in scorecard.get("experiments") or []:
        status = entry.get("status", "?")
        title = entry.get("title", entry.get("id", ""))
        line = f"  [{status:7}] {entry.get('id', '')} - {title}"
        print(line)
        if entry.get("abort_reason"):
            print(f"           guardrail: {entry['abort_reason']}")
        elif entry.get("error") and status in ("failed", "aborted"):
            err = str(entry["error"]).splitlines()[0]
            print(f"           {err}")


def _cmd_scorecard(args: argparse.Namespace) -> int:
    report_path = Path(args.report)
    if not report_path.is_file():
        print(f"Report not found: {report_path}", file=sys.stderr)
        return 2
    data = json.loads(report_path.read_text(encoding="utf-8"))
    scorecard = scorecard_from_report(data)
    if not scorecard:
        print("No experiment scorecard in report (run `mcp-test experiment run` first).", file=sys.stderr)
        return 2
    _print_scorecard(scorecard)
    return 0


async def _cmd_run_async(args: argparse.Namespace) -> int:
    catalog = _catalog_from_arg(args.catalog)
    try:
        ids = resolve_experiment_ids(
            experiment_id=args.experiment_id,
            suite=args.suite,
            catalog=catalog,
        )
    except (KeyError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    if not args.server_command:
        cfg_path = Path(args.config) if args.config else _discover_config_file()
        if cfg_path is None or not cfg_path.is_file():
            print("Error: --server-command is required (or set server.command in mcp-test.yaml).", file=sys.stderr)
            return 2

    cfg_path = Path(args.config) if args.config else _discover_config_file()
    if cfg_path is not None and cfg_path.is_file():
        errors = validate_config_file(cfg_path)
        if errors:
            print(f"Configuration validation failed for {cfg_path}:", file=sys.stderr)
            for err in errors:
                print(f"  - {err.message}", file=sys.stderr)
            return 2

    try:
        config = load_config(_config_namespace(args))
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 2

    results = await run_experiments(config, ids, catalog=catalog)

    console = ConsoleReporter()
    print(console.generate(results))

    scorecard = (results.unified_summary or {}).get("experiments") or {}
    if scorecard:
        print()
        _print_scorecard(scorecard)

    if config.report_format and config.report_output:
        report_path = Path(config.report_output)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        if config.report_format == "json":
            text = JSONReporter().generate(results)
        elif config.report_format == "html":
            from mcp_test_harness.html_reporter import HTMLReporter

            text = HTMLReporter().generate(results)
        if text is not None:
            report_path.write_text(text, encoding="utf-8")
            logger.info("Report written to %s", report_path)

    if results.failed > 0 or results.errored > 0:
        return 1
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    log_level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(level=log_level, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    return asyncio.run(_cmd_run_async(args))


def run_experiment_main(argv: list[str] | None = None) -> int:
    """Entry point for `mcp-test experiment`."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "list":
        return _cmd_list(args)
    if args.command == "scorecard":
        return _cmd_scorecard(args)
    if args.command == "run":
        return _cmd_run(args)
    raise AssertionError(f"unknown experiment command: {args.command}")
