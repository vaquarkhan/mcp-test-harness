"""`mcp-test try` and `mcp-test conformance` — zero-config conformance (RFC-002)."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from argparse import Namespace
from pathlib import Path
from typing import Any

from mcp_test_harness.config import HarnessConfig, _discover_config_file, load_config, validate_config_file
from mcp_test_harness.conformance import (
    LEVEL_NAMES,
    badge_markdown,
    conformance_from_report,
    evaluate_conformance,
)
from mcp_test_harness.lifecycle import ServerLifecycleManager, StartupError
from mcp_test_harness.reporting import ConsoleReporter, JSONReporter

logger = logging.getLogger(__name__)


def _config_ns(args: argparse.Namespace) -> Namespace:
    return Namespace(
        test_path="tests",
        version=False,
        list=False,
        watch=False,
        config=getattr(args, "config", None),
        server_command=getattr(args, "server_command", None),
        transport=getattr(args, "transport", None),
        timeout=getattr(args, "timeout", None),
        verbose=getattr(args, "verbose", False),
        parallel=None,
        workers=None,
        report_format=getattr(args, "report_format", None),
        report_output=getattr(args, "report_output", None),
        pdf_output=None,
        sarif_output=None,
        pr_summary_output=None,
        update_snapshots=None,
        filter_name=None,
        filter_marker=None,
        fail_fast=False,
        last_failed=False,
    )


def _print_conformance(card: dict[str, Any]) -> None:
    name = card.get("name", "None")
    level = card.get("level", -1)
    print(f"Conformance: {name} (level {level})")
    levels = card.get("levels") or {}
    for key in ("boot", "protocol", "covered", "secure", "resilient"):
        mark = "PASS" if levels.get(key) else "-"
        print(f"  [{mark:4}] {key}")
    for reason in card.get("reasons") or []:
        print(f"  note: {reason}")
    badge = card.get("badge") or {}
    md = badge.get("markdown")
    if md:
        print()
        print("README badge:")
        print(f"  {md}")


async def _probe_boot_protocol(config: HarnessConfig) -> tuple[bool, bool, str | None]:
    """Return (boot, protocol, error_message)."""
    from mcp_test_harness.schema import SchemaValidator, validate_mcp_server_after_connect

    lifecycle = ServerLifecycleManager()
    server: Any = None
    try:
        try:
            server = await lifecycle.start(config)
        except StartupError as exc:
            return False, False, str(exc)
        await server.session.list_tools()
        if not config.schema_validation:
            return True, True, None
        viol = await validate_mcp_server_after_connect(
            server.session,
            server.init_result,
            SchemaValidator(True),
            schema_probe_call_tool=config.schema_probe_call_tool,
        )
        if viol:
            msg = "; ".join(v.message for v in viol[:8])
            return True, False, msg
        return True, True, None
    finally:
        if server is not None:
            await lifecycle.shutdown(server)


async def _try_async(args: argparse.Namespace) -> int:
    cfg_path = Path(args.config) if args.config else _discover_config_file()
    if not args.server_command and (cfg_path is None or not Path(cfg_path).is_file()):
        print(
            "Error: --server-command is required (or set server.command in mcp-test.yaml).",
            file=sys.stderr,
        )
        print(
            'Example: mcp-test try --server-command "uvx awslabs.roda-mcp-server@latest"',
            file=sys.stderr,
        )
        return 2

    if cfg_path is not None and Path(cfg_path).is_file():
        errors = validate_config_file(Path(cfg_path))
        if errors:
            print(f"Configuration validation failed for {cfg_path}:", file=sys.stderr)
            for err in errors:
                print(f"  - {err.message}", file=sys.stderr)
            return 2

    try:
        config = load_config(_config_ns(args))
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 2

    if args.no_schema:
        from dataclasses import replace

        config = replace(config, schema_validation=False)

    print("mcp-test try -- zero-config conformance probe (RFC-002)")
    print(f"  Server: {config.server_command!r}")
    print(f"  Transport: {config.transport}")
    print()

    boot, protocol, err = await _probe_boot_protocol(config)
    if not boot:
        print(f"Boot failed: {err}", file=sys.stderr)
        card = evaluate_conformance(boot=False, protocol=False)
        _print_conformance(card)
        return 1

    if not protocol:
        print(f"Protocol checks failed: {err}", file=sys.stderr)

    card = evaluate_conformance(boot=boot, protocol=protocol)
    results = None

    if args.suite:
        from mcp_test_harness.experiments.loader import load_catalog
        from mcp_test_harness.experiments.runner import resolve_experiment_ids, run_experiments
        from mcp_test_harness.conformance import attach_conformance

        catalog = load_catalog()
        try:
            ids = resolve_experiment_ids(suite=args.suite, catalog=catalog)
        except KeyError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 2
        print(f"Running experiment suite {args.suite!r} ({len(ids)} experiments)...")
        results = await run_experiments(config, ids, catalog=catalog)
        print(ConsoleReporter().generate(results))
        card = attach_conformance(results, boot=True, protocol=protocol and results.unified_summary.get("gate") != "n/a")

    print()
    _print_conformance(card)

    if args.report_format and args.report_output:
        out = Path(args.report_output)
        out.parent.mkdir(parents=True, exist_ok=True)
        if results is not None:
            if args.report_format == "json":
                out.write_text(JSONReporter().generate(results), encoding="utf-8")
            elif args.report_format == "html":
                from mcp_test_harness.html_reporter import HTMLReporter

                out.write_text(HTMLReporter().generate(results), encoding="utf-8")
        else:
            payload = {
                "mode": "try",
                "unified_summary": {"gate": "pass" if protocol else "fail", "conformance": card},
                "conformance": card,
            }
            out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Report written to {out}")

    if not protocol:
        return 1
    if results is not None and (results.failed > 0 or results.errored > 0):
        return 1
    return 0


def _cmd_try(argv: list[str] | None) -> int:
    p = argparse.ArgumentParser(
        prog="mcp-test try",
        description="Zero-config conformance probe: boot + protocol (optional experiment suite).",
    )
    p.add_argument("--server-command", dest="server_command", default=None)
    p.add_argument("--config", default=None)
    p.add_argument("--transport", default=None, choices=["stdio", "sse", "http"])
    p.add_argument("--timeout", type=float, default=None)
    p.add_argument("--verbose", action="store_true")
    p.add_argument("--no-schema", action="store_true", help="Skip post-connect schema validation")
    p.add_argument(
        "--suite",
        default=None,
        help="Also run resiliency experiment suite (e.g. core)",
    )
    p.add_argument("--report-format", dest="report_format", choices=["json", "html"], default=None)
    p.add_argument("--report-output", dest="report_output", default=None)
    args = p.parse_args(argv)
    log_level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(level=log_level, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    return asyncio.run(_try_async(args))


def _cmd_conformance(argv: list[str] | None) -> int:
    p = argparse.ArgumentParser(
        prog="mcp-test conformance",
        description="Grade conformance from a JSON report or print a README badge.",
    )
    # Shared so both `grade --report X` and `badge --report X` work the same way.
    p.add_argument(
        "--report",
        default=None,
        help="Path to mcp-test JSON report (grade from file; badge uses report level when set)",
    )
    sub = p.add_subparsers(dest="command")

    grade = sub.add_parser("grade", help="Grade a JSON report (default if --report given)")
    grade.add_argument(
        "--report",
        default=None,
        dest="grade_report",
        help="Path to mcp-test JSON report",
    )

    badge = sub.add_parser(
        "badge",
        help="Print markdown badge (from --report level, or --level name)",
    )
    badge.add_argument(
        "--report",
        default=None,
        dest="badge_report",
        help="JSON report path - badge uses the graded level from this report",
    )
    badge.add_argument(
        "--level",
        default=None,
        choices=list(LEVEL_NAMES.values()) + ["None"],
        help="Explicit level name (ignored when --report is set)",
    )

    stateless = sub.add_parser(
        "stateless",
        help="SEP-2575 adversarial conformance (Streamable HTTP, no initialize handshake)",
    )
    stateless.add_argument(
        "--url",
        required=True,
        help="MCP server HTTP endpoint (e.g. http://localhost:8080/mcp)",
    )
    stateless.add_argument(
        "--protocol-version",
        default="2026-07-28",
        dest="protocol_version",
        help="Expected MCP protocol version (default: 2026-07-28)",
    )
    stateless.add_argument(
        "--generate-badge",
        action="store_true",
        help="Print README badge markdown on success",
    )
    stateless.add_argument("--verbose", action="store_true")

    args = p.parse_args(argv)

    if args.command == "stateless":
        from mcp_test_harness.stateless.conformance import (
            StatelessConformanceGate,
            stateless_badge_markdown,
        )

        if args.verbose:
            logging.basicConfig(
                level=logging.INFO,
                format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            )
        print(f"mcp-test conformance stateless — SEP-2575 / SEP-2243")
        print(f"  URL: {args.url}")
        print(f"  Protocol: {args.protocol_version}")
        print()
        gate = StatelessConformanceGate(
            args.url,
            protocol_version=args.protocol_version,
        )
        ok = gate.run_all()
        for check in gate.results:
            mark = "PASS" if check.passed else "FAIL"
            print(f"  [{mark}] {check.test_name}: {check.details}")
        print()
        if ok:
            print("SERVER CERTIFIED: 100% stateless conformance (SEP-2575 / SEP-2243)")
            if args.generate_badge:
                print("\nREADME badge:")
                print(f"  {stateless_badge_markdown()}")
            return 0
        print("SERVER NON-COMPLIANT: fix header / schema enforcement (see failures above).", file=sys.stderr)
        return 1

    def _resolve_report() -> str | None:
        for attr in ("grade_report", "badge_report", "report"):
            val = getattr(args, attr, None)
            if val:
                return str(val)
        return None

    if args.command == "badge":
        report_path = _resolve_report()
        if report_path:
            path = Path(report_path)
            if not path.is_file():
                print(f"Report not found: {path}", file=sys.stderr)
                return 2
            data = json.loads(path.read_text(encoding="utf-8"))
            card = conformance_from_report(data)
            print(badge_markdown(str(card.get("name") or "None")))
            return 0
        level = args.level or "Protocol"
        print(badge_markdown(level))
        return 0

    report_path = _resolve_report()
    if not report_path:
        p.print_help()
        return 2

    path = Path(report_path)
    if not path.is_file():
        print(f"Report not found: {path}", file=sys.stderr)
        return 2
    data = json.loads(path.read_text(encoding="utf-8"))
    card = conformance_from_report(data)
    _print_conformance(card)
    return 0


def run_try(argv: list[str] | None = None) -> int:
    """Entry for `mcp-test try`."""
    return _cmd_try(argv)


def run_conformance(argv: list[str] | None = None) -> int:
    """Entry for `mcp-test conformance`."""
    return _cmd_conformance(argv)
