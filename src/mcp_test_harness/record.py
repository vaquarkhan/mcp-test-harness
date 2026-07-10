"""Record live MCP tool calls into a reviewable test suite (RFC-001)."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from argparse import Namespace
from pathlib import Path
from typing import Any

from mcp_test_harness.assertions import _serialize
from mcp_test_harness.generate import _tool_name, _tool_schema, example_arguments
from mcp_test_harness.snapshots import SnapshotManager

_RECORDED_HEADER = '''"""
Auto-recorded MCP tests — review and edit before merging.

Created by: mcp-test record (RFC-001)
Run: mcp-test --config mcp-test.yaml
"""

from __future__ import annotations

from pathlib import Path

from mcp_test_harness import (
    assert_snapshot,
    assert_tool_call,
    marker,
)
'''


def _safe_ident(name: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in name) or "tool"


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
        verbose=False,
        parallel=None,
        workers=None,
        report_format=None,
        report_output=None,
        pdf_output=None,
        sarif_output=None,
        pr_summary_output=None,
        update_snapshots=None,
        filter_name=None,
        filter_marker=None,
        fail_fast=False,
        last_failed=False,
    )


def load_cassette(path: Path) -> list[dict[str, Any]]:
    """Load ``calls`` from a JSON cassette file."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        calls = data
    elif isinstance(data, dict):
        calls = data.get("calls") or []
    else:
        raise ValueError("cassette must be a list or object with 'calls'")
    if not isinstance(calls, list):
        raise ValueError("'calls' must be a list")
    out: list[dict[str, Any]] = []
    for item in calls:
        if not isinstance(item, dict):
            continue
        tool = item.get("tool") or item.get("name")
        if not tool:
            continue
        args = item.get("arguments") or item.get("args") or {}
        if not isinstance(args, dict):
            args = {}
        entry: dict[str, Any] = {"tool": str(tool), "arguments": args}
        if "response" in item:
            entry["response"] = item["response"]
        if item.get("error"):
            entry["error"] = str(item["error"])
        out.append(entry)
    return out


def render_recorded_module(calls: list[dict[str, Any]]) -> str:
    """Render Python tests from recorded call dicts."""
    lines: list[str] = [_RECORDED_HEADER.strip(), ""]
    seen: set[str] = set()
    for call in calls:
        if call.get("error"):
            continue
        name = str(call["tool"])
        args = call.get("arguments") or {}
        safe = _safe_ident(name)
        snap = f"recorded_{safe}"
        # Disambiguate duplicate tool names
        base = safe
        n = 2
        while safe in seen:
            safe = f"{base}_{n}"
            snap = f"recorded_{safe}"
            n += 1
        seen.add(safe)
        args_repr = repr(args)
        lines.append("")
        lines.append('@marker(tags=["smoke", "recorded"])')
        lines.append(f"async def test_recorded_{safe}(mcp_server) -> None:")
        lines.append(f'    """Recorded happy-path for tool ``{name}``."""')
        lines.append(f"    result = await assert_tool_call(mcp_server, {name!r}, {args_repr})")
        lines.append(
            f"    await assert_snapshot(result, {snap!r}, test_file=Path(__file__))"
        )
    if not any("async def test_recorded_" in ln for ln in lines):
        lines.append("")
        lines.append('@marker(tags=["recorded"])')
        lines.append("async def test_recorded_no_calls(mcp_server) -> None:")
        lines.append('    """No successful calls were recorded."""')
        lines.append("    await mcp_server.list_tools()")
    return "\n".join(lines) + "\n"


def write_snapshots_for_calls(out_path: Path, calls: list[dict[str, Any]]) -> int:
    """Write ``__snapshots__/recorded_*.snap`` beside *out_path*. Returns count."""
    mgr = SnapshotManager(update=True)
    written = 0
    seen: set[str] = set()
    for call in calls:
        if call.get("error") or "response" not in call:
            continue
        name = str(call["tool"])
        safe = _safe_ident(name)
        base = safe
        n = 2
        while safe in seen:
            safe = f"{base}_{n}"
            n += 1
        seen.add(safe)
        snap_name = f"recorded_{safe}"
        path = mgr.get_snapshot_path(out_path, snap_name)
        mgr.write_snapshot(path, _serialize(call["response"]))
        written += 1
    return written


def _build_record_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="mcp-test record",
        description="Record live tool calls into a reviewable test suite (RFC-001).",
    )
    p.add_argument(
        "--out",
        default="tests/test_mcp_recorded.py",
        help="Output test file (default: tests/test_mcp_recorded.py)",
    )
    p.add_argument("--config", default=None, help="Path to mcp-test.yaml / mcp-test.toml")
    p.add_argument("--server-command", default=None, help="Override server.command")
    p.add_argument("--transport", default=None, choices=["stdio", "sse", "http"])
    p.add_argument("--timeout", type=float, default=None, help="Per-call timeout seconds")
    p.add_argument("--force", action="store_true", help="Overwrite existing output file")
    p.add_argument(
        "--tools",
        default=None,
        help="Comma-separated tool names to record (default: all)",
    )
    p.add_argument("--max-tools", type=int, default=None, help="Cap number of tools recorded")
    p.add_argument(
        "--from-json",
        default=None,
        help="JSON cassette with calls[{tool,arguments,response?}]; skips live discovery when responses present",
    )
    p.add_argument(
        "--no-snapshots",
        action="store_true",
        help="Do not write __snapshots__ files",
    )
    p.add_argument(
        "--session-json",
        default=None,
        help="Also write raw recorded calls JSON to this path",
    )
    return p


async def _record_live(config: Any, tool_filter: set[str] | None, max_tools: int | None) -> list[dict[str, Any]]:
    from mcp_test_harness.lifecycle import ServerLifecycleManager, StartupError

    lifecycle = ServerLifecycleManager()
    server = None
    calls: list[dict[str, Any]] = []
    try:
        try:
            server = await lifecycle.start(config)
        except StartupError as exc:
            print(f"record: server failed to start: {exc}", file=sys.stderr)
            raise SystemExit(1) from exc
        res = await server.session.list_tools()
        tools = list(getattr(res, "tools", None) or [])
        selected: list[Any] = []
        for tool in tools:
            name = _tool_name(tool)
            if not name or name == "unknown":
                continue
            if tool_filter is not None and name not in tool_filter:
                continue
            selected.append(tool)
            if max_tools is not None and len(selected) >= max_tools:
                break
        for tool in selected:
            name = _tool_name(tool)
            args = example_arguments(_tool_schema(tool))
            entry: dict[str, Any] = {"tool": name, "arguments": args}
            try:
                result = await server.session.call_tool(name, args)
                entry["response"] = _serialize(result)
            except Exception as exc:  # noqa: BLE001 — record failure per tool
                entry["error"] = str(exc)
                print(f"record: tool {name!r} failed: {exc}", file=sys.stderr)
            calls.append(entry)
        return calls
    finally:
        if server is not None:
            await lifecycle.shutdown(server)


async def _fill_missing_responses(
    config: Any,
    calls: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Live-call any cassette entries that lack a response."""
    need = [c for c in calls if "response" not in c and not c.get("error")]
    if not need:
        return calls
    from mcp_test_harness.lifecycle import ServerLifecycleManager, StartupError

    lifecycle = ServerLifecycleManager()
    server = None
    try:
        try:
            server = await lifecycle.start(config)
        except StartupError as exc:
            print(f"record: server failed to start: {exc}", file=sys.stderr)
            raise SystemExit(1) from exc
        for c in need:
            try:
                result = await server.session.call_tool(c["tool"], c["arguments"])
                c["response"] = _serialize(result)
            except Exception as exc:  # noqa: BLE001 — record failure per tool
                c["error"] = str(exc)
                print(f"record: tool {c['tool']!r} failed: {exc}", file=sys.stderr)
        return calls
    finally:
        if server is not None:
            await lifecycle.shutdown(server)


async def run_record_async(argv: list[str] | None) -> int:
    from mcp_test_harness.config import load_config

    parser = _build_record_parser()
    args = parser.parse_args(argv)
    out_path = Path(args.out).resolve()

    if out_path.exists() and not args.force:
        print(f"Refusing to overwrite {out_path} (use --force).", file=sys.stderr)
        return 2

    tool_filter: set[str] | None = None
    if args.tools:
        tool_filter = {t.strip() for t in args.tools.split(",") if t.strip()}

    ns = _config_ns(args)
    try:
        config = load_config(ns)
    except SystemExit:
        return 2

    if args.from_json:
        cassette_path = Path(args.from_json)
        if not cassette_path.is_file():
            print(f"record: cassette not found: {cassette_path}", file=sys.stderr)
            return 2
        try:
            calls = load_cassette(cassette_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"record: invalid cassette: {exc}", file=sys.stderr)
            return 2
        if tool_filter is not None:
            calls = [c for c in calls if c["tool"] in tool_filter]
        if args.max_tools is not None:
            calls = calls[: args.max_tools]
        # If any call lacks response, fill from live server when configured
        if any("response" not in c and not c.get("error") for c in calls):
            # Fill from live server when we have a command; otherwise emit call-only tests.
            if config.server_command or args.server_command or args.config:
                calls = await _fill_missing_responses(config, calls)
    else:
        calls = await _record_live(config, tool_filter, args.max_tools)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    source = render_recorded_module(calls)
    out_path.write_text(source, encoding="utf-8")
    print(f"Wrote {out_path} ({sum(1 for c in calls if not c.get('error'))} call(s))")

    snap_count = 0
    if not args.no_snapshots:
        snap_count = write_snapshots_for_calls(out_path, calls)
        if snap_count:
            print(f"Wrote {snap_count} snapshot(s) under {out_path.parent / '__snapshots__'}")

    if args.session_json:
        session_path = Path(args.session_json)
        session_path.parent.mkdir(parents=True, exist_ok=True)
        session_path.write_text(
            json.dumps({"calls": calls}, indent=2, default=str) + "\n",
            encoding="utf-8",
        )
        print(f"Wrote session cassette to {session_path}")

    print("\nNext: review recorded tests, then run: mcp-test", out_path)
    return 0


def run_record(argv: list[str] | None = None) -> int:
    return asyncio.run(run_record_async(argv))
