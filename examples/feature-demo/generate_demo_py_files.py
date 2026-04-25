"""Generate runnable Python demo tests for each feature scenario.

Run from repo root:
    python examples/feature-demo/generate_demo_py_files.py
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent


OUT_DIR = Path(__file__).resolve().parent / "python-scenarios"


COMMON_HEADER = dedent(
    """
    \"\"\"Feature demo scenario test.

    Update placeholder tool/resource/prompt names for your MCP server.
    Run with:
        mcp-test --server-command "python -m your_server" examples/feature-demo/python-scenarios
    \"\"\"
    from __future__ import annotations

    from pathlib import Path

    from mcp_test_harness import (
        assert_capabilities,
        assert_invalid_tool,
        assert_latency,
        assert_prompt,
        assert_protocol_version,
        assert_resource_list,
        assert_resource_read,
        assert_snapshot,
        assert_tool_call,
        assert_tool_call_validates_input,
        assert_tool_idempotent,
        assert_tool_list,
        assert_tool_rejects,
        assert_tool_schema,
        marker,
        skip,
    )
    """
).strip() + "\n\n"


def _scenario_code(n: int) -> str:
    bodies: dict[int, str] = {
        1: """
async def test_demo_01_assert_tool_call(mcp_server):
    await assert_tool_call(mcp_server, "echo", {"text": "hello"})
""",
        2: """
async def test_demo_02_assert_tool_list(mcp_server):
    await assert_tool_list(mcp_server, ["echo", "health"])
""",
        3: """
async def test_demo_03_assert_tool_schema(mcp_server):
    await assert_tool_schema(
        mcp_server,
        "echo",
        {"type": "object", "properties": {"text": {"type": "string"}}},
    )
""",
        4: """
async def test_demo_04_assert_tool_rejects(mcp_server):
    await assert_tool_rejects(mcp_server, "echo", {"text": 123})
""",
        5: """
async def test_demo_05_assert_invalid_tool(mcp_server):
    await assert_invalid_tool(mcp_server, "tool_that_does_not_exist")
""",
        6: """
async def test_demo_06_assert_tool_call_validates_input(mcp_server):
    await assert_tool_call_validates_input(mcp_server, "echo", {"text": 999})
""",
        7: """
async def test_demo_07_validate_against_input_schema(mcp_server):
    await assert_tool_call(
        mcp_server,
        "echo",
        {"text": "hello"},
        validate_against_input_schema=True,
    )
""",
        8: """
async def test_demo_08_assert_resource_read(mcp_server):
    await assert_resource_read(mcp_server, "resource://status")
""",
        9: """
async def test_demo_09_assert_resource_list(mcp_server):
    await assert_resource_list(mcp_server, ["resource://status"])
""",
        10: """
async def test_demo_10_assert_prompt(mcp_server):
    await assert_prompt(mcp_server, "summarize", {"text": "hello world"})
""",
        11: """
async def test_demo_11_assert_capabilities(mcp_server):
    await assert_capabilities(mcp_server, {"tools": {}})
""",
        12: """
async def test_demo_12_assert_snapshot(mcp_server):
    result = await assert_tool_call(mcp_server, "echo", {"text": "snapshot"})
    await assert_snapshot(result, "demo_12_snapshot", test_file=Path(__file__))
""",
        13: """
async def test_demo_13_assert_snapshot_ignore(mcp_server):
    result = await assert_tool_call(mcp_server, "echo", {"text": "ignore"})
    await assert_snapshot(
        result,
        "demo_13_snapshot_ignore",
        test_file=Path(__file__),
        ignore_fields=["timestamp", "requestId"],
    )
""",
        14: """
async def test_demo_14_assert_snapshot_mask(mcp_server):
    result = await assert_tool_call(mcp_server, "echo", {"text": "mask"})
    await assert_snapshot(
        result,
        "demo_14_snapshot_mask",
        test_file=Path(__file__),
        mask_patterns=[r"req_[a-zA-Z0-9_\\-]+"],
    )
""",
        15: """
async def test_demo_15_assert_protocol_version(mcp_server):
    await assert_protocol_version(mcp_server, expected="2024-11-05")
""",
        16: """
async def test_demo_16_assert_tool_idempotent(mcp_server):
    await assert_tool_idempotent(mcp_server, "echo", {"text": "same"}, runs=3)
""",
        17: """
@marker(tags=["perf"])
async def test_demo_17_assert_latency_single(mcp_server):
    await assert_latency(mcp_server, "echo", {"text": "speed"}, max_ms=500.0)
""",
        18: """
@marker(tags=["perf"])
async def test_demo_18_assert_latency_p95(mcp_server):
    await assert_latency(
        mcp_server, "echo", {"text": "p95"}, max_ms=800.0, runs=20, aggregate="p95"
    )
""",
        19: """
@marker(tags=["perf"])
async def test_demo_19_assert_latency_p99(mcp_server):
    await assert_latency(
        mcp_server, "echo", {"text": "p99"}, max_ms=1200.0, runs=30, aggregate="p99"
    )
""",
        20: """
@marker(tags=["perf"])
async def test_demo_20_assert_latency_mean(mcp_server):
    await assert_latency(
        mcp_server, "echo", {"text": "mean"}, max_ms=700.0, runs=15, aggregate="mean"
    )
""",
        21: """
@marker(tags=["perf"])
async def test_demo_21_assert_latency_median(mcp_server):
    await assert_latency(
        mcp_server, "echo", {"text": "median"}, max_ms=700.0, runs=15, aggregate="median"
    )
""",
        22: """
@marker(tags=["perf"])
async def test_demo_22_assert_latency_warmup(mcp_server):
    await assert_latency(
        mcp_server, "echo", {"text": "warmup"}, max_ms=700.0, warmup=3, runs=10, aggregate="p95"
    )
""",
        23: """
async def test_demo_23_mcp_server_fixture(mcp_server):
    # Fresh session per test
    await assert_tool_call(mcp_server, "echo", {"text": "fixture-per-test"})
""",
        24: """
async def test_demo_24_mcp_server_session_fixture(mcp_server_session):
    # Shared session across tests in this module
    await assert_tool_call(mcp_server_session, "echo", {"text": "fixture-per-module"})
""",
        25: """
@marker(timeout=5)
async def test_demo_25_marker_timeout(mcp_server):
    await assert_tool_call(mcp_server, "echo", {"text": "timeout-marker"})
""",
        26: """
@marker(retry=2)
async def test_demo_26_marker_retry(mcp_server):
    await assert_tool_call(mcp_server, "echo", {"text": "retry-marker"})
""",
        27: """
@marker(tags=["smoke", "integration"])
async def test_demo_27_marker_tags(mcp_server):
    await assert_tool_call(mcp_server, "echo", {"text": "tagged"})
""",
        28: """
@marker(order=1)
async def test_demo_28_marker_order(mcp_server):
    await assert_tool_call(mcp_server, "echo", {"text": "ordered"})
""",
        29: """
@skip
async def test_demo_29_skip(mcp_server):
    await assert_tool_call(mcp_server, "echo", {"text": "skipped"})
""",
        30: """
@skip(reason="Demonstration skip reason")
async def test_demo_30_skip_with_reason(mcp_server):
    await assert_tool_call(mcp_server, "echo", {"text": "skipped-with-reason"})
""",
    }
    return dedent(bodies[n]).strip() + "\n"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    slugs = [
        "assert_tool_call",
        "assert_tool_list",
        "assert_tool_schema",
        "assert_tool_rejects",
        "assert_invalid_tool",
        "assert_tool_call_validates_input",
        "validate_against_input_schema",
        "assert_resource_read",
        "assert_resource_list",
        "assert_prompt",
        "assert_capabilities",
        "assert_snapshot",
        "assert_snapshot_ignore",
        "assert_snapshot_mask",
        "assert_protocol_version",
        "assert_tool_idempotent",
        "assert_latency_single",
        "assert_latency_p95",
        "assert_latency_p99",
        "assert_latency_mean",
        "assert_latency_median",
        "assert_latency_warmup",
        "mcp_server_fixture",
        "mcp_server_session_fixture",
        "marker_timeout",
        "marker_retry",
        "marker_tags",
        "marker_order",
        "skip",
        "skip_with_reason",
    ]

    for idx, slug in enumerate(slugs, start=1):
        fn = OUT_DIR / f"test_demo_{idx:02d}_{slug}.py"
        fn.write_text(COMMON_HEADER + _scenario_code(idx), encoding="utf-8")
        print(fn.relative_to(Path(__file__).resolve().parents[2]))


if __name__ == "__main__":
    main()

