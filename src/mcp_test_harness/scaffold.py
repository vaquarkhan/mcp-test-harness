"""Scaffold starter tests and config (`mcp-test init`) for a fast on-ramp."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Embedded templates (no package-data layout required for wheel installs)
# ---------------------------------------------------------------------------

_MCP_TEST_YAML = """# MCP Test Harness — edit server.command to point at your MCP server.
# Docs: https://github.com/vaquarkhan/mcp-test-harness/blob/main/docs/DEVELOPER_GUIDE.md

server:
  command: __SERVER_COMMAND__

test_dirs:
  - tests

# Optional:
# transport: stdio
# schema_validation: true
"""

_TEST_PY = '''"""
MCP server tests — starter file created by `mcp-test init`.

Run with:  mcp-test  (or mcp-test --config mcp-test.yaml)

Replace tool names and assertions with checks that match your server.
"""

from __future__ import annotations

from mcp_test_harness import (
    assert_latency,
    assert_tool_call,
    assert_tool_list,
    marker,
    skip,
)


@marker(tags=["smoke"])
async def test_server_list_tools_succeeds(mcp_server) -> None:
    """Harness session can call list_tools (empty tool list is OK)."""
    res = await mcp_server.list_tools()
    tools = getattr(res, "tools", None) or []
    assert isinstance(tools, list)


async def test_expected_tools_if_you_know_them(mcp_server) -> None:
    """Uncomment and list tool names your server must expose (subset check)."""
    # await assert_tool_list(mcp_server, ["my_tool", "other_tool"])


@skip(reason="Remove @skip and set a real tool + arguments for your server")
async def test_call_tool_example(mcp_server) -> None:
    """Un-skip and set a real tool name from list_tools()."""
    # await assert_tool_call(
    #     mcp_server,
    #     "example_tool",
    #     {"query": "hello"},
    #     validate_against_input_schema=True,
    # )


# @marker(tags=["perf"])
# async def test_tool_latency_budget(mcp_server) -> None:
#     """Uncomment: enforce max latency (see docs on assert_latency, PERFORMANCE.md)."""
#     # await assert_latency(
#     #     mcp_server, "example_tool", {}, max_ms=200.0, runs=3, aggregate="p95", warmup=1
#     # )
'''


def _build_init_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="mcp-test init",
        description="Create a starter tests/ file and optional mcp-test.yaml in the current project.",
    )
    p.add_argument(
        "--dir",
        dest="root",
        default=".",
        help="Project root to write files under (default: .)",
    )
    p.add_argument(
        "--tests-subdir",
        default="tests",
        help="Directory for the test file (created if missing; default: tests)",
    )
    p.add_argument(
        "--filename",
        default="test_mcp_server_example.py",
        help="Test file name (default: test_mcp_server_example.py)",
    )
    p.add_argument(
        "--server-command",
        default="python -m your_server  # TODO: replace with your MCP server command",
        help="Value for server.command in mcp-test.yaml (quoted for your shell if needed)",
    )
    p.add_argument(
        "--no-config",
        action="store_true",
        help="Do not write mcp-test.yaml (only create the test file)",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files if they already exist",
    )
    return p


def run_init(argv: list[str] | None) -> int:
    """Entry point for ``mcp-test init``."""
    parser = _build_init_parser()
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    tests_dir = root / args.tests_subdir
    test_path = tests_dir / args.filename
    config_path = root / "mcp-test.yaml"

    tests_dir.mkdir(parents=True, exist_ok=True)

    if test_path.exists() and not args.force:
        print(
            f"Refusing to overwrite existing file: {test_path}\n"
            "  Use --force to replace it.",
            file=sys.stderr,
        )
        return 2

    test_path.write_text(_TEST_PY.strip() + "\n", encoding="utf-8")
    print(f"Wrote {test_path}")

    if not args.no_config:
        if config_path.exists() and not args.force:
            print(
                f"Skipped mcp-test.yaml (already exists): {config_path}\n"
                "  Use --force to overwrite, or merge server.command manually.",
                file=sys.stderr,
            )
        else:
            # YAML-safe quoted server command (spaces, quotes, colons in argv)
            cmd_yaml = f"  command: {json.dumps(args.server_command)}\n"
            yaml_text = _MCP_TEST_YAML.replace("  command: __SERVER_COMMAND__\n", cmd_yaml)
            config_path.write_text(yaml_text, encoding="utf-8")
            print(f"Wrote {config_path}")

    print("\nNext steps:")
    print(f"  1. Edit server command in {config_path if not args.no_config else 'mcp-test.yaml (create or use --no-config)'}")
    print(f"  2. Implement real tests in {test_path.name}")
    print("  3. Run:  mcp-test --config mcp-test.yaml  (or place mcp-test.yaml in CWD)")
    return 0
