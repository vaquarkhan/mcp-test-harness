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
from mcp_test_harness.config import load_config
from mcp_test_harness.discovery import discover_tests
from mcp_test_harness.reporting import ConsoleReporter

logger = logging.getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the ``mcp-test`` CLI."""
    parser = argparse.ArgumentParser(
        prog="mcp-test",
        description="MCP Test Harness -- a pytest-style testing framework for MCP servers.",
        epilog="Tip: run `mcp-test init` in your project to scaffold a starter test file and mcp-test.yaml.",
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
        choices=["json", "junit", "html"],
        help="Report output format",
    )
    parser.add_argument(
        "--report-output",
        dest="report_output",
        default=None,
        help="Path to write the report file",
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
) -> int:
    """Single harness execution: discover, (optionally) run, report. Returns exit code."""
    from mcp_test_harness.html_reporter import HTMLReporter
    from mcp_test_harness.plugins import PluginRegistry
    from mcp_test_harness.reporting import JSONReporter, JUnitXMLReporter
    from mcp_test_harness.scheduler import HarnessScheduler

    test_dirs = [Path(d) for d in config.test_dirs]
    modules = discover_tests(
        paths=test_dirs,
        filter_name=config.filter_name,
        filter_marker=config.filter_marker,
    )
    all_cases = [tc for mod in modules for tc in mod.test_cases]
    if not all_cases:
        print("No tests discovered.")
        return 0
    if list_only:
        for mod in modules:
            for tc in mod.test_cases:
                print(f"{mod.path}::{tc.name}")
        return 0

    registry = PluginRegistry()
    registry.discover_and_load(config)

    scheduler = HarnessScheduler()
    if config.parallel:
        results = await scheduler.run_parallel(
            all_cases, config, workers=config.workers
        )
    else:
        results = await scheduler.run_sequential(all_cases, config)

    console_reporter = ConsoleReporter()
    print(console_reporter.generate(results))

    report_text: str | None = None
    if config.report_format == "json":
        report_text = JSONReporter().generate(results)
    elif config.report_format == "junit":
        report_text = JUnitXMLReporter().generate(results)
    elif config.report_format == "html":
        report_text = HTMLReporter().generate(results)
    if report_text is not None and config.report_output:
        output_path = Path(config.report_output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report_text, encoding="utf-8")
        logger.info("Report written to %s", output_path)
    if results.failed > 0 or results.errored > 0:
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
            await _run_harness(config, list_only=False)
            outer += 1
            if watch_max_outer and outer >= watch_max_outer:
                return 0
            while True:  # pragma: no cover (infinite watch poll; run via --watch in dev)
                await asyncio.sleep(watch_interval)  # pragma: no cover
                snap = _test_tree_snapshot(test_dirs)  # pragma: no cover
                if snap != state:  # pragma: no cover
                    # Wait until the tree is stable across debounce to coalesce rapid saves.
                    last = snap
                    while True:  # pragma: no cover
                        await asyncio.sleep(watch_debounce)  # pragma: no cover
                        snap2 = _test_tree_snapshot(test_dirs)  # pragma: no cover
                        if snap2 == last:  # pragma: no cover
                            state = snap2  # pragma: no cover
                            break  # pragma: no cover
                        last = snap2  # pragma: no cover
                    break  # pragma: no cover

    return await _run_harness(config, list_only=bool(args.list))


def main(argv: list[str] | None = None) -> int:
    """Sync entry point for the ``mcp-test`` console script.

    Wraps the async core via ``asyncio.run()``.
    """
    av = list(sys.argv[1:] if argv is None else argv)
    if av and av[0] == "init":
        from mcp_test_harness.scaffold import run_init

        return run_init(av[1:])
    return asyncio.run(_async_main(av))


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover (subprocess runs in a separate Python process without coverage tracing)
