"""Tests for stdio_mcp: failure paths and cleanup."""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.client.stdio import StdioServerParameters

from mcp_test_harness.stdio_mcp import stdio_client_exposing_process


@pytest.mark.asyncio
async def test_stdio_client_oserror_cleans_up_streams() -> None:
    """If process creation fails, memory streams are closed and OSError propagates."""
    with patch(
        "mcp_test_harness.stdio_mcp._create_platform_compatible_process",
        side_effect=OSError("spawn failed"),
    ):
        p = StdioServerParameters(command="nope", args=[])
        with pytest.raises(OSError, match="spawn failed"):
            async with stdio_client_exposing_process(p):
                pytest.fail("should not enter body")  # pragma: no cover


@pytest.mark.asyncio
async def test_stdio_wait_timeout_terminates_tree() -> None:
    proc = MagicMock()
    proc.stdin = MagicMock()
    proc.stdin.aclose = AsyncMock()
    proc.stdout = MagicMock()
    proc.wait = AsyncMock(side_effect=TimeoutError())

    @asynccontextmanager
    async def fake_tg():
        yield MagicMock(start_soon=MagicMock())

    with (
        patch(
            "mcp_test_harness.stdio_mcp._create_platform_compatible_process",
            AsyncMock(return_value=proc),
        ),
        patch("mcp_test_harness.stdio_mcp.anyio.create_task_group", fake_tg),
        patch("mcp_test_harness.stdio_mcp._terminate_process_tree", AsyncMock()) as term,
    ):
        p = StdioServerParameters(command="echo", args=["x"])
        async with stdio_client_exposing_process(p):
            pass
        term.assert_awaited_once()
