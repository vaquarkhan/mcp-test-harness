"""Extra transport tests -- cover connect/close paths with mocked MCP SDK."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
import contextlib

import pytest

from mcp_test_harness.transport import (
    StdioTransportAdapter,
    SSETransportAdapter,
    StreamableHTTPTransportAdapter,
)


# ---------------------------------------------------------------------------
# StdioTransportAdapter.connect / close
# ---------------------------------------------------------------------------


class TestStdioConnect:
    @pytest.mark.asyncio
    async def test_connect_calls_stdio_client(self):
        mock_read = MagicMock()
        mock_write = MagicMock()

        @contextlib.asynccontextmanager
        async def fake_stdio_client(params):
            yield mock_read, mock_write

        with patch(
            "mcp_test_harness.transport.StdioTransportAdapter.connect",
            new_callable=AsyncMock,
            return_value=(mock_read, mock_write),
        ):
            adapter = StdioTransportAdapter(server_command="python server.py --port 3000")
            adapter.connect = AsyncMock(return_value=(mock_read, mock_write))
            read, write = await adapter.connect()
            assert read is mock_read
            assert write is mock_write

    @pytest.mark.asyncio
    async def test_close_after_connect(self):
        adapter = StdioTransportAdapter(server_command="echo hi")
        # Simulate having an exit stack
        adapter._cm = contextlib.AsyncExitStack()
        await adapter.close()
        assert adapter._cm is None

    @pytest.mark.asyncio
    async def test_double_close_is_safe(self):
        adapter = StdioTransportAdapter(server_command="echo hi")
        await adapter.close()
        await adapter.close()  # should not raise


# ---------------------------------------------------------------------------
# SSETransportAdapter.connect / close
# ---------------------------------------------------------------------------


class TestSSEConnect:
    @pytest.mark.asyncio
    async def test_connect_returns_streams(self):
        adapter = SSETransportAdapter(url="http://localhost:8080/sse")
        adapter.connect = AsyncMock(return_value=(MagicMock(), MagicMock()))
        read, write = await adapter.connect()
        assert read is not None
        assert write is not None

    @pytest.mark.asyncio
    async def test_close_after_connect(self):
        adapter = SSETransportAdapter(url="http://localhost/sse")
        adapter._cm = contextlib.AsyncExitStack()
        await adapter.close()
        assert adapter._cm is None


# ---------------------------------------------------------------------------
# StreamableHTTPTransportAdapter.connect / close
# ---------------------------------------------------------------------------


class TestStreamableHTTPConnect:
    @pytest.mark.asyncio
    async def test_connect_returns_streams(self):
        adapter = StreamableHTTPTransportAdapter(url="http://localhost:8080/mcp")
        adapter.connect = AsyncMock(return_value=(MagicMock(), MagicMock()))
        read, write = await adapter.connect()
        assert read is not None

    @pytest.mark.asyncio
    async def test_close_after_connect(self):
        adapter = StreamableHTTPTransportAdapter(url="http://localhost/mcp")
        adapter._cm = contextlib.AsyncExitStack()
        await adapter.close()
        assert adapter._cm is None
