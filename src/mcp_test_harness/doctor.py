"""`mcp-test doctor` — connect to a server, verify handshake, optionally schema checks, list surfaces.

No test files required. Uses the same config as normal runs (``mcp-test.yaml`` or flags).
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from argparse import Namespace
from dataclasses import replace
from typing import Any

from mcp_test_harness.config import HarnessConfig, load_config
from mcp_test_harness.lifecycle import ServerLifecycleManager, StartupError


def _ns_from_doctor_args(args: argparse.Namespace) -> Namespace:
    """Build a :class:`Namespace` compatible with :func:`load_config`."""
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
        report_format=None,
        report_output=None,
        update_snapshots=None,
        filter_name=None,
        filter_marker=None,
    )


def _tool_name(t: Any) -> str:
    n = getattr(t, "name", None)
    if n is not None:
        return str(n)
    return str(t)[:80]


async def _doctor_async(config: HarnessConfig) -> int:
    """Start server, print protocol / inventory, optional schema validation."""
    from mcp_test_harness.schema import SchemaValidator, validate_mcp_server_after_connect

    lifecycle = ServerLifecycleManager()
    server: Any = None
    code = 0
    try:
        try:
            server = await lifecycle.start(config)
        except StartupError as exc:
            print(f"doctor: server failed to start: {exc}", file=sys.stderr)
            return 1
        assert server is not None

        proto = ServerLifecycleManager.protocol_version_from_init(server.init_result)
        caps = server.capabilities
        cap_keys = sorted(str(k) for k in (caps or {}).keys())

        print("mcp-test doctor — quick health check (no tests run)")
        print()
        print(f"  Transport:     {config.transport}")
        print(f"  Server command: {config.server_command!r}")
        print(f"  Protocol:      {proto or '— (not reported by server)'}")
        print(
            f"  Capabilities:  {', '.join(cap_keys[:12])}{'…' if len(cap_keys) > 12 else ''}"
            if cap_keys
            else "  Capabilities:  —"
        )

        session = server.session
        n_tools = n_res = n_pr = 0
        err_lines: list[str] = []

        try:
            lt = await session.list_tools()
            tools = getattr(lt, "tools", None)
            if tools is None and isinstance(lt, list):
                tools = lt
            tools = tools or []
            n_tools = len(tools)
            print()
            print(f"  Tools ({n_tools}):")
            for t in tools[:20]:
                print(f"    • {_tool_name(t)}")
            if n_tools > 20:
                print(f"    … {n_tools - 20} more")
        except Exception as exc:  # noqa: BLE001
            err_lines.append(f"list_tools: {exc}")

        try:
            lr = await session.list_resources()
            res = getattr(lr, "resources", None)
            if res is None and isinstance(lr, list):
                res = lr
            res = res or []
            n_res = len(res)
            print()
            print(f"  Resources ({n_res})")
        except Exception as exc:  # noqa: BLE001
            err_lines.append(f"list_resources: {exc}")

        try:
            lp = await session.list_prompts()
            prompts = getattr(lp, "prompts", None)
            if prompts is None and isinstance(lp, list):
                prompts = lp
            prompts = prompts or []
            n_pr = len(prompts)
            print()
            print(f"  Prompts ({n_pr})")
        except Exception as exc:  # noqa: BLE001
            err_lines.append(f"list_prompts: {exc}")

        if err_lines and not (n_tools or n_res or n_pr):
            for line in err_lines:
                print(f"  Warning: {line}", file=sys.stderr)

        if config.schema_validation:
            print()
            print("  Schema validation (post-connect checks)…")
            viol = await validate_mcp_server_after_connect(
                server.session,
                server.init_result,
                SchemaValidator(True),
                schema_probe_call_tool=config.schema_probe_call_tool,
            )
            if viol:
                print(f"  Schema: FAIL — {len(viol)} issue(s):")
                for v in viol[:20]:
                    print(f"    - {v.message}")
                if len(viol) > 20:
                    print(f"    … and {len(viol) - 20} more")
                code = 1
            else:
                print("  Schema: OK")
        else:
            print()
            print("  Schema validation: skipped (--no-schema or config)")

        print()
        if code == 0:
            print("Result: healthy (doctor checks passed).")
        else:
            print("Result: failed schema validation (see above).", file=sys.stderr)
        return code
    finally:
        if server is not None:
            await lifecycle.shutdown(server)


def run_doctor(argv: list[str]) -> int:
    """Entry point: ``mcp-test doctor [options]``."""
    p = argparse.ArgumentParser(
        prog="mcp-test doctor",
        description=(
            "Start the configured MCP server, run initialize, list tools/resources/prompts, "
            "and optionally run the same post-connect schema checks as the test harness. "
            "Does not require any test files."
        ),
    )
    p.add_argument(
        "--config",
        default=None,
        help="Config file (default: auto-discover mcp-test.yaml in cwd)",
    )
    p.add_argument(
        "--server-command",
        default=None,
        help="Override server start command (same as mcp-test --server-command)",
    )
    p.add_argument(
        "--transport",
        default=None,
        choices=["stdio", "sse", "http"],
        help="Transport (default: stdio or from config)",
    )
    p.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="Handshake and request timeout in seconds (default: 30)",
    )
    p.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose logging",
    )
    p.add_argument(
        "--no-schema",
        action="store_true",
        help="Do not run post-connect MCP shape / schema checks",
    )
    args = p.parse_args(argv)

    import logging

    log_level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    try:
        config = load_config(_ns_from_doctor_args(args))
    except SystemExit as exc:
        c = exc.code
        return c if isinstance(c, int) else 2

    if args.no_schema:
        config = replace(config, schema_validation=False)

    return asyncio.run(_doctor_async(config))
