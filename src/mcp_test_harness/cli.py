"""CLI entry point for the MCP Test Harness.

Parses command-line arguments, loads configuration, discovers tests,
runs them through the scheduler, and generates reports.

Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 12.4, 12.5
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

from mcp_test_harness import __version__
from mcp_test_harness.config import _discover_config_file, load_config, validate_config_file
from mcp_test_harness.discovery import discover_tests
from mcp_test_harness.reporting import ConsoleReporter

logger = logging.getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the ``mcp-test`` CLI."""
    parser = argparse.ArgumentParser(
        prog="mcp-test",
        description="MCP Test Harness -- a pytest-style testing framework for MCP servers.",
        epilog=(
            "Tip: run `mcp-test init` in your project to scaffold tests; "
            "`mcp-test generate` drafts tests from tools/list; "
            "`mcp-test experiment list` shows resiliency experiment templates; "
            "`mcp-test try` runs a zero-config conformance probe; "
            "`mcp-test doctor` checks server handshake and lists tools (no tests required)."
        ),
    )

    parser.add_argument(
        "test_path",
        nargs="?",
        default=None,
        help="Path to test directory or file (default: from config or tests/)",
    )
    parser.add_argument(
        "--server-command",
        dest="server_command",
        default=None,
        help="Shell command to start the MCP server under test",
    )
    parser.add_argument(
        "--transport",
        default=None,
        choices=["stdio", "sse", "http"],
        help="Transport type (default: stdio)",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to configuration file (mcp-test.yaml / mcp-test.toml)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=None,
        help="Enable verbose output including full server communication logs",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="Default per-test timeout in seconds (default: 30)",
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        default=None,
        help="Run tests in parallel across multiple workers",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Number of parallel workers (default: CPU count)",
    )
    parser.add_argument(
        "--report-format",
        dest="report_format",
        default=None,
        choices=["json", "junit", "html", "sarif"],
        help="Report output format",
    )
    parser.add_argument(
        "--report-output",
        dest="report_output",
        default=None,
        help="Path to write the report file",
    )
    parser.add_argument(
        "--pdf-output",
        dest="pdf_output",
        default=None,
        help=(
            "When used with --report-format html, also export a PDF summary "
            "(requires Chrome/Edge; or use Save as PDF in the HTML report)"
        ),
    )
    parser.add_argument(
        "--sarif-output",
        dest="sarif_output",
        default=None,
        help="Path to write SARIF security findings (in addition to --report-format)",
    )
    parser.add_argument(
        "--cra-output",
        dest="cra_output",
        default=None,
        help=(
            "Path to write CRA Annex I conformity matrix JSON (opt-in; "
            "see docs/CRA_COMPLIANCE.md)"
        ),
    )
    parser.add_argument(
        "--pr-summary-output",
        dest="pr_summary_output",
        default=None,
        help="Path to write a markdown PR summary comment",
    )
    parser.add_argument(
        "--update-snapshots",
        dest="update_snapshots",
        action="store_true",
        default=None,
        help="Overwrite existing snapshot files with current responses",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        default=False,
        help="Print version and exit",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        default=False,
        help="List discovered tests and exit without running them",
    )
    parser.add_argument(
        "-k",
        dest="filter_name",
        default=None,
        help="Filter tests by name pattern (substring or glob)",
    )
    parser.add_argument(
        "-m",
        dest="filter_marker",
        default=None,
        help="Filter tests by marker or tag",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        default=False,
        help=(
            "Re-run tests when .py files under the test paths change (polling; "
            "MCP_TEST_HARNESS_WATCH_INTERVAL, MCP_TEST_HARNESS_WATCH_DEBOUNCE)"
        ),
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        default=False,
        help="Stop after the first test failure, error, or timeout (skip remaining as SKIPPED).",
    )
    parser.add_argument(
        "--last-failed",
        action="store_true",
        default=False,
        help="Re-run only tests that failed, errored, or timed out in the previous run (see .mcp_test_harness/last-failed.json).",
    )

    return parser


def _test_tree_snapshot(test_dirs: list[Path]) -> tuple[tuple[str, float], ...]:
    """Return (path, mtime) for all Python files under *test_dirs*."""
    entries: list[tuple[str, float]] = []
    for d in test_dirs:
        p = Path(d)
        if p.is_file() and p.suffix == ".py":
            entries.append((str(p.resolve()), p.stat().st_mtime))
        elif p.is_dir():
            for f in p.rglob("*.py"):
                try:
                    entries.append((str(f.resolve()), f.stat().st_mtime))
                except OSError:
                    continue
    return tuple(sorted(entries))


async def _run_harness(
    config,
    list_only: bool,
    *,
    fail_fast: bool = False,
    last_failed: bool = False,
) -> int:
    """Single harness execution: discover, (optionally) run, report. Returns exit code."""
    from mcp_test_harness.snapshots import reset_cli_update_snapshots, set_cli_update_snapshots

    update_token = set_cli_update_snapshots(bool(getattr(config, "update_snapshots", False)))
    try:
        return await _run_harness_impl(
            config,
            list_only,
            fail_fast=fail_fast,
            last_failed=last_failed,
        )
    finally:
        reset_cli_update_snapshots(update_token)


async def _run_harness_impl(
    config,
    list_only: bool,
    *,
    fail_fast: bool = False,
    last_failed: bool = False,
) -> int:
    """Internal harness body (runs under the CLI snapshot-update context)."""
    from mcp_test_harness.html_reporter import HTMLReporter
    from mcp_test_harness.last_failed_cache import (
        filter_harness_cases,
        keys_from_session_results,
        read_last_failed_keys,
        write_last_failed_keys,
    )
    from mcp_test_harness.plugins import PluginRegistry
    from mcp_test_harness.pr_summary import generate_pr_summary
    from mcp_test_harness.cra_reporter import CRATechnicalDocumentReporter
    from mcp_test_harness.reporting import JSONReporter, JUnitXMLReporter
    from mcp_test_harness.sarif_reporter import SARIFReporter
    from mcp_test_harness.scheduler import HarnessScheduler

    registry = PluginRegistry()
    registry.discover_and_load(config)
    registry.expose_assertions()

    test_dirs = [Path(d) for d in config.test_dirs]
    modules = discover_tests(
        paths=test_dirs,
        filter_name=config.filter_name,
        filter_marker=config.filter_marker,
    )
    modules = registry.apply_discovery_hooks(modules)
    all_cases = [tc for mod in modules for tc in mod.test_cases]

    if last_failed:
        lf_keys = read_last_failed_keys()
        if not lf_keys:
            print("No tests to run: last-failed cache is empty.", file=sys.stderr)
            return 0
        all_cases = filter_harness_cases(all_cases, lf_keys)
        if not all_cases:
            print("No tests matched --last-failed filter.", file=sys.stderr)
            return 0
    elif not all_cases:
        # Non-zero like pytest's "no tests collected" (exit 5) so CI cannot
        # green-pass a misconfigured test.dirs / empty discovery.
        print("No tests discovered.", file=sys.stderr)
        return 5
    if list_only:
        by_mod: dict[Path, list] = {}
        for tc in all_cases:
            by_mod.setdefault(tc.module_path, []).append(tc)
        for mod_path in sorted(by_mod.keys(), key=str):
            for tc in by_mod[mod_path]:
                print(f"{mod_path}::{tc.name}")
        return 0

    scheduler = HarnessScheduler()
    if config.parallel:
        results = await scheduler.run_parallel(
            all_cases,
            config,
            workers=config.workers,
            plugin_registry=registry,
            fail_fast=fail_fast,
        )
    else:
        results = await scheduler.run_sequential(
            all_cases, config, plugin_registry=registry, fail_fast=fail_fast
        )

    console_reporter = ConsoleReporter()
    print(console_reporter.generate(results))

    if config.report_output and not config.report_format:
        print(
            "Warning: --report-output is ignored without --report-format "
            "(json|junit|html|sarif).",
            file=sys.stderr,
        )

    report_text: str | None = None
    if config.report_format == "json":
        report_text = JSONReporter().generate(results)
    elif config.report_format == "junit":
        report_text = JUnitXMLReporter().generate(results)
    elif config.report_format == "html":
        report_text = HTMLReporter().generate(results)
    elif config.report_format == "sarif":
        report_text = SARIFReporter().generate(results)
    if report_text is not None and config.report_output:
        output_path = Path(config.report_output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report_text, encoding="utf-8")
        logger.info("Report written to %s", output_path)
        if config.report_format == "html" and config.pdf_output:
            from mcp_test_harness.pdf_export import export_html_to_pdf

            pdf_path = Path(config.pdf_output)
            try:
                export_html_to_pdf(output_path, pdf_path)
                logger.info("PDF report written to %s", pdf_path)
            except (OSError, RuntimeError) as exc:
                logger.warning("PDF export skipped: %s", exc)
                print(f"Warning: PDF export failed: {exc}", file=sys.stderr)

    # Always honor --sarif-output (even when --report-format sarif), unless it
    # would duplicate the primary report_output path already written above.
    sarif_path = config.sarif_output
    if sarif_path:
        primary = Path(config.report_output) if config.report_output else None
        sp = Path(sarif_path)
        if primary is None or sp.resolve() != primary.resolve():
            sarif_text = SARIFReporter().generate(results)
            sp.parent.mkdir(parents=True, exist_ok=True)
            sp.write_text(sarif_text, encoding="utf-8")
            logger.info("SARIF report written to %s", sp)

    cra_path = config.cra_output
    if cra_path:
        cra_text = CRATechnicalDocumentReporter().generate(results)
        cp = Path(cra_path)
        cp.parent.mkdir(parents=True, exist_ok=True)
        cp.write_text(cra_text, encoding="utf-8")
        logger.info("CRA conformity matrix written to %s", cp)

    if config.pr_summary_output:
        summary_text = generate_pr_summary(results)
        pp = Path(config.pr_summary_output)
        pp.parent.mkdir(parents=True, exist_ok=True)
        pp.write_text(summary_text, encoding="utf-8")
        logger.info("PR summary written to %s", pp)
    if not list_only:
        write_last_failed_keys(keys_from_session_results(results))

    if results.failed > 0 or results.errored > 0:
        return 1
    # Opt-in quality_gate (e.g. require_security_tests) can fail with 0 test failures.
    qg = (results.unified_summary or {}).get("quality_gate") or {}
    if qg.get("status") == "fail":
        reasons = qg.get("reasons") or []
        if reasons:
            print("Quality gate failed: " + "; ".join(reasons), file=sys.stderr)
        return 1
    return 0


async def _async_main(argv: list[str] | None = None) -> int:
    """Async core of the CLI.

    Returns exit code: 0 = all passed, 1 = failures/errors, 2 = config error.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    # --version: print and exit early  (Req 12.5)
    if args.version:
        print(f"mcp-test {__version__}")
        return 0

    # Configure logging  (Req 7.7)
    log_level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Validate config before load so users get an aggregated error list.
    cfg_path = Path(args.config) if args.config else _discover_config_file()
    if cfg_path is not None and cfg_path.is_file():
        cfg_errors = validate_config_file(cfg_path)
        if cfg_errors:
            print(f"Configuration validation failed for {cfg_path}:", file=sys.stderr)
            for err in cfg_errors:
                if err.line is not None:
                    print(f"  - line {err.line}: {err.message}", file=sys.stderr)
                else:
                    print(f"  - {err.message}", file=sys.stderr)
            return 2

    # Load config -- merges CLI flags + config file  (Req 7.4, 7.5)
    try:
        config = load_config(args)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 2

    if args.list and args.watch:
        print("Error: --watch is not supported with --list", file=sys.stderr)
        return 2

    test_dirs = [Path(d) for d in config.test_dirs]
    if args.watch:
        # Optional cap for tests (0 = unlimited; one outer iteration = one harness run)
        watch_max_outer = int(os.environ.get("MCP_TEST_HARNESS_WATCH_MAX_OUTER", "0") or 0)
        watch_interval = float(os.environ.get("MCP_TEST_HARNESS_WATCH_INTERVAL", "1.0") or 1.0)
        watch_debounce = float(os.environ.get("MCP_TEST_HARNESS_WATCH_DEBOUNCE", "0.4") or 0.4)
        print(
            f"Watch mode: re-run when test *.py change "
            f"(poll {watch_interval:g}s, debounce {watch_debounce:g}s). Ctrl+C to stop.",
            file=sys.stderr,
        )
        state = _test_tree_snapshot(test_dirs)
        outer = 0
        while watch_max_outer == 0 or outer < watch_max_outer:
            await _run_harness(
                config,
                list_only=False,
                fail_fast=bool(args.fail_fast),
                last_failed=bool(args.last_failed),
            )
            outer += 1
            if watch_max_outer and outer >= watch_max_outer:
                return 0
            while True:
                await asyncio.sleep(watch_interval)
                snap = _test_tree_snapshot(test_dirs)
                if snap != state:
                    # Wait until the tree is stable across debounce to coalesce rapid saves.
                    last = snap
                    while True:
                        await asyncio.sleep(watch_debounce)
                        snap2 = _test_tree_snapshot(test_dirs)
                        if snap2 == last:
                            state = snap2
                            break
                        last = snap2
                    break

    if args.list and args.fail_fast:
        print("Error: --list cannot be used with --fail-fast", file=sys.stderr)
        return 2

    return await _run_harness(
        config,
        list_only=bool(args.list),
        fail_fast=bool(args.fail_fast),
        last_failed=bool(args.last_failed),
    )


def main(argv: list[str] | None = None) -> int:
    """Sync entry point for the ``mcp-test`` console script.

    Wraps the async core via ``asyncio.run()``.
    """
    from mcp_test_harness.console_io import configure_stdio

    configure_stdio()
    av = list(sys.argv[1:] if argv is None else argv)
    if av and av[0] == "init":
        from mcp_test_harness.scaffold import run_init

        return run_init(av[1:])
    if av and av[0] == "doctor":
        from mcp_test_harness.doctor import run_doctor

        return run_doctor(av[1:])
    if av and av[0] == "generate":
        from mcp_test_harness.generate import run_generate

        return run_generate(av[1:])
    if av and av[0] == "record":
        from mcp_test_harness.record import run_record

        return run_record(av[1:])
    if av and av[0] == "export-pdf":
        from mcp_test_harness.pdf_export import run_export_pdf

        return run_export_pdf(av[1:])
    if av and av[0] == "experiment":
        from mcp_test_harness.experiments.cli import run_experiment_main

        return run_experiment_main(av[1:])
    if av and av[0] == "try":
        from mcp_test_harness.try_cli import run_try

        return run_try(av[1:])
    if av and av[0] == "conformance":
        from mcp_test_harness.try_cli import run_conformance

        return run_conformance(av[1:])
    return asyncio.run(_async_main(av))


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover (subprocess runs in a separate Python process without coverage tracing)
