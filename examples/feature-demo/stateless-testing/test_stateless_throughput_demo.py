"""Stateless throughput demo — runs only when MCP_STATELESS_URL is set."""

from __future__ import annotations

import os

import pytest

from mcp_test_harness import assert_stateless_throughput, marker

_URL = os.environ.get("MCP_STATELESS_URL", "").strip()


@marker(tags=["perf", "stateless"])
@pytest.mark.asyncio
@pytest.mark.skipif(not _URL, reason="Set MCP_STATELESS_URL to a 2026-07-28 Streamable HTTP endpoint")
async def test_stateless_throughput_demo() -> None:
    await assert_stateless_throughput(
        target_url=_URL,
        tool_name=os.environ.get("MCP_STATELESS_TOOL", "echo"),
        arguments={"message": "stateless-load"},
        duration_s=float(os.environ.get("MCP_STATELESS_DURATION", "3")),
        concurrency=int(os.environ.get("MCP_STATELESS_CONCURRENCY", "8")),
        min_rps=float(os.environ.get("MCP_STATELESS_MIN_RPS", "1")),
        max_p99_ms=float(os.environ.get("MCP_STATELESS_MAX_P99_MS", "5000")),
        max_error_rate=float(os.environ.get("MCP_STATELESS_MAX_ERROR_RATE", "5")),
    )
