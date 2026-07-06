"""Platform QA demos (v1.3): MCP trace, chaos faults, and report artifacts.

Run against any server that exposes an ``echo`` tool (same contract as other feature-demo packs).
Traces appear automatically in HTML/JSON reports — no extra test code required.
"""

from __future__ import annotations

from mcp_test_harness import marker
from mcp_test_harness.assertions import assert_tool_call
from mcp_test_harness.chaos import ChaosFaultError


@marker(tags=["smoke", "trace-demo"])
async def test_echo_records_mcp_trace(mcp_server) -> None:
    """Every call_tool is captured in mcp_trace when report format is html/json."""
    await assert_tool_call(mcp_server, "echo", {"text": "trace-timeline-demo"})


@marker(tags=["chaos", "resiliency"], chaos_faults=["delay_ms:75"])
async def test_survives_injected_latency(mcp_server) -> None:
    await assert_tool_call(mcp_server, "echo", {"text": "slow-path"})


@marker(tags=["chaos", "resiliency"], chaos_faults=["truncate"])
async def test_truncated_response_still_has_content(mcp_server) -> None:
    result = await assert_tool_call(
        mcp_server,
        "echo",
        {"text": "long-body-for-truncation-chaos-fault-injection"},
    )
    content = getattr(result, "content", None) or []
    assert content, "truncated response should still return content items"


@marker(tags=["chaos", "negative"], chaos_faults=["503"])
async def test_simulated_503_raises_chaos_fault(mcp_server) -> None:
    try:
        await mcp_server.call_tool("echo", {"text": "unavailable"})
        raise AssertionError("expected ChaosFaultError from 503 fault")
    except ChaosFaultError as exc:
        assert exc.code == 503


@marker(tags=["chaos", "contract"], chaos_faults=["schema_drift"])
async def test_schema_drift_on_json_payload(mcp_server) -> None:
    result = await mcp_server.call_tool("echo", {"text": '{"user_id": 42, "role": "viewer"}'})
    text = result.content[0].text
    assert text  # drift may rename user_id → id; inspect in HTML trace timeline
