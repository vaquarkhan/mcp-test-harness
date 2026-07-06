"""Offline test scaffolding from live MCP server inventory (`mcp-test generate`)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_GENERATED_HEADER = '''"""
Auto-generated MCP tests — review and edit before merging.

Created by: mcp-test generate
Run: mcp-test --config mcp-test.yaml
"""

from __future__ import annotations

from mcp_test_harness import (
    assert_tool_call,
    assert_tool_rejects,
    marker,
    skip,
)
'''

def _tool_name(tool: Any) -> str:
    n = getattr(tool, "name", None)
    if n is not None:
        return str(n)
    if isinstance(tool, dict):
        return str(tool.get("name", "unknown"))
    return "unknown"


def _tool_schema(tool: Any) -> dict[str, Any]:
    schema = getattr(tool, "inputSchema", None)
    if schema is None and isinstance(tool, dict):
        schema = tool.get("inputSchema")
    if isinstance(schema, dict):
        return schema
    return {}


def _example_value(prop_schema: dict[str, Any], key: str) -> Any:
    if "enum" in prop_schema and prop_schema["enum"]:
        return prop_schema["enum"][0]
    typ = prop_schema.get("type", "string")
    if typ == "integer":
        return prop_schema.get("minimum", 0) or 1
    if typ == "number":
        return float(prop_schema.get("minimum", 0) or 1.0)
    if typ == "boolean":
        return True
    if typ == "array":
        return []
    if typ == "object":
        return {}
    return f"example_{key}"


def example_arguments(input_schema: dict[str, Any]) -> dict[str, Any]:
    """Build minimal valid-ish arguments from JSON Schema properties."""
    props = input_schema.get("properties") or {}
    if not isinstance(props, dict):
        return {}
    required = list(input_schema.get("required") or [])
    keys = required if required else list(props.keys())[:3]
    args: dict[str, Any] = {}
    for key in keys:
        if key in props and isinstance(props[key], dict):
            args[key] = _example_value(props[key], key)
        else:
            args[key] = f"example_{key}"
    return args


def render_test_module(
    tools: list[Any],
    *,
    include_edge_cases: bool = True,
) -> str:
    """Render Python test source for discovered tools."""
    lines: list[str] = [_GENERATED_HEADER.strip(), ""]
    for tool in tools:
        name = _tool_name(tool)
        if not name or name == "unknown":
            continue
        schema = _tool_schema(tool)
        args = example_arguments(schema)
        args_repr = repr(args)
        safe_name = "".join(c if c.isalnum() else "_" for c in name)
        lines.append("")
        lines.append('@marker(tags=["smoke", "generated"])')
        lines.append(f"async def test_tool_{safe_name}_happy_path(mcp_server) -> None:")
        lines.append(f'    """Happy-path call for tool ``{name}``.""')
        lines.append(f"    await assert_tool_call(mcp_server, {name!r}, {args_repr})")
        if include_edge_cases:
            lines.append("")
            lines.append("@skip(reason='Generated edge case — tailor invalid payload')")
            lines.append("@marker(tags=['generated', 'edge'])")
            lines.append(f"async def test_tool_{safe_name}_rejects_bad_input(mcp_server) -> None:")
            lines.append(f'    """Tool ``{name}`` should reject invalid input.""')
            lines.append(
                f"    await assert_tool_rejects(mcp_server, {name!r}, {{'__invalid__': True}})"
            )
    if not any("async def test_" in ln for ln in lines):
        lines.append("")
        lines.append("@skip(reason='No tools discovered — run mcp-test doctor to verify server')")
        lines.append("async def test_no_tools_discovered(mcp_server) -> None:")
        lines.append("    await mcp_server.list_tools()")
    return "\n".join(lines) + "\n"


def _build_generate_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="mcp-test generate",
        description="Generate Python tests from live tools/list (offline artifact for review).",
    )
    p.add_argument("--dir", dest="root", default=".", help="Project root (default: .)")
    p.add_argument("--tests-subdir", default="tests", help="Output directory (default: tests)")
    p.add_argument(
        "--filename",
        default="test_mcp_generated.py",
        help="Output file name (default: test_mcp_generated.py)",
    )
    p.add_argument("--config", default=None, help="Path to mcp-test.yaml / mcp-test.toml")
    p.add_argument("--server-command", default=None, help="Override server.command")
    p.add_argument("--transport", default=None, choices=["stdio", "sse", "http"])
    p.add_argument("--no-edge-cases", action="store_true", help="Skip edge-case stub tests")
    p.add_argument("--force", action="store_true", help="Overwrite existing output file")
    p.add_argument(
        "--drift-report",
        default=None,
        help="Write JSON report comparing tools to existing generated file",
    )
    return p


async def _fetch_tools(config: Any) -> list[Any]:
    from mcp_test_harness.lifecycle import ServerLifecycleManager, StartupError

    lifecycle = ServerLifecycleManager()
    server = None
    try:
        server = await lifecycle.start(config)
        res = await server.session.list_tools()
        tools = getattr(res, "tools", None) or []
        return list(tools)
    except StartupError as exc:
        print(f"generate: server failed to start: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    finally:
        if server is not None:
            await lifecycle.shutdown(server)


def _drift_report(existing_path: Path, tool_names: list[str]) -> dict[str, Any]:
    text = existing_path.read_text(encoding="utf-8") if existing_path.is_file() else ""
    missing_tests = [n for n in tool_names if f'"{n}"' not in text and f"'{n}'" not in text]
    return {
        "tools_advertised": tool_names,
        "existing_file": str(existing_path),
        "tools_missing_from_tests": missing_tests,
        "drift_detected": bool(missing_tests),
    }


async def run_generate_async(argv: list[str] | None) -> int:
    from argparse import Namespace

    from mcp_test_harness.config import load_config

    parser = _build_generate_parser()
    args = parser.parse_args(argv)
    ns = Namespace(
        test_path="tests",
        version=False,
        list=False,
        watch=False,
        config=args.config,
        server_command=args.server_command,
        transport=args.transport,
        timeout=None,
        verbose=False,
        parallel=None,
        workers=None,
        report_format=None,
        report_output=None,
        sarif_output=None,
        pr_summary_output=None,
        update_snapshots=None,
        filter_name=None,
        filter_marker=None,
        fail_fast=False,
        last_failed=False,
    )
    try:
        config = load_config(ns)
    except SystemExit:
        return 2

    tools = await _fetch_tools(config)
    tool_names = [_tool_name(t) for t in tools]

    root = Path(args.root).resolve()
    out_dir = root / args.tests_subdir
    out_path = out_dir / args.filename
    out_dir.mkdir(parents=True, exist_ok=True)

    if out_path.exists() and not args.force:
        print(
            f"Refusing to overwrite {out_path} (use --force).",
            file=sys.stderr,
        )
        if args.drift_report:
            report = _drift_report(out_path, tool_names)
            Path(args.drift_report).write_text(json.dumps(report, indent=2), encoding="utf-8")
            print(f"Wrote drift report to {args.drift_report}")
        return 2

    source = render_test_module(tools, include_edge_cases=not args.no_edge_cases)
    out_path.write_text(source, encoding="utf-8")
    print(f"Wrote {out_path} ({len(tool_names)} tool(s))")
    if args.drift_report:
        report = _drift_report(out_path, tool_names)
        Path(args.drift_report).write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Wrote drift report to {args.drift_report}")
    print("\nNext: review generated tests, remove @skip where appropriate, run mcp-test")
    return 0


def run_generate(argv: list[str] | None) -> int:
    import asyncio

    return asyncio.run(run_generate_async(argv))
