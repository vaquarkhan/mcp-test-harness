"""CLI entry point for the MCP Test Harness.

Parses command-line arguments, loads configuration, discovers tests,
runs them through the scheduler, and generates reports.

Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 12.4, 12.5
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from mcp_test_harness import __version__
from mcp_test_harness.config import load_config
from mcp_test_harness.discovery import discover_tests
from mcp_test_harness.plugins import PluginRegistry
from mcp_test_harness.reporting import ConsoleReporter, JSONReporter, JUnitXMLReporter
from mcp_test_harness.scheduler import HarnessScheduler

logger = logging.getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the ``mcp-test`` CLI."""
    parser = argparse.ArgumentParser(
        prog="mcp-test",
        description="MCP Test Harness -- a pytest-style testing framework for MCP servers.",
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
        choices=["json", "junit"],
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

    return parser


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

    # Load plugins  (Req 9.1, 9.2)
    registry = PluginRegistry()
    registry.discover_and_load(config)

    # Discover tests  (Req 2.1, 2.2, 2.3, 2.7)
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

    # Run tests via scheduler  (Req 13.1, 13.5)
    scheduler = HarnessScheduler()
    if config.parallel:
        results = await scheduler.run_parallel(
            all_cases, config, workers=config.workers
        )
    else:
        results = await scheduler.run_sequential(all_cases, config)

    # Generate console report (always)  (Req 6.1)
    console_reporter = ConsoleReporter()
    print(console_reporter.generate(results))

    # Generate additional report if requested  (Req 6.2, 6.3)
    report_text: str | None = None
    if config.report_format == "json":
        report_text = JSONReporter().generate(results)
    elif config.report_format == "junit":
        report_text = JUnitXMLReporter().generate(results)

    # Write report to file if --report-output specified
    if report_text is not None and config.report_output:
        output_path = Path(config.report_output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report_text, encoding="utf-8")
        logger.info("Report written to %s", output_path)

    # Exit code  (Req 7.6)
    if results.failed > 0 or results.errored > 0:
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    """Sync entry point for the ``mcp-test`` console script.

    Wraps the async core via ``asyncio.run()``.
    """
    return asyncio.run(_async_main(argv))


if __name__ == "__main__":
    sys.exit(main())
