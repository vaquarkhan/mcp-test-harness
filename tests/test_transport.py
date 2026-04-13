"""Unit tests for mcp_test_harness.transport."""

from __future__ import annotations

import pytest

from mcp_test_harness.transport import (
    SSETransportAdapter,
    StdioTransportAdapter,
    StreamableHTTPTransportAdapter,
    TransportAdapter,
    create_transport_adapter,
)


# ---------------------------------------------------------------------------
# TransportAdapter protocol conformance
# ---------------------------------------------------------------------------


class TestProtocolConformance:
    """Verify concrete adapters satisfy the TransportAdapter protocol."""

    def test_stdio_is_transport_adapter(self) -> None:
        adapter = StdioTransportAdapter(server_command="echo hello")
        assert isinstance(adapter, TransportAdapter)

    def test_sse_is_transport_adapter(self) -> None:
        adapter = SSETransportAdapter(url="http://localhost:8080/sse")
        assert isinstance(adapter, TransportAdapter)

    def test_streamable_http_is_transport_adapter(self) -> None:
        adapter = StreamableHTTPTransportAdapter(url="http://localhost:8080/mcp")
        assert isinstance(adapter, TransportAdapter)


# ---------------------------------------------------------------------------
# Factory function
# ---------------------------------------------------------------------------


class TestCreateTransportAdapter:
    """Tests for the ``create_transport_adapter`` factory."""

    def test_stdio_returns_stdio_adapter(self) -> None:
        adapter = create_transport_adapter("stdio", "python server.py")
        assert isinstance(adapter, StdioTransportAdapter)

    def test_sse_returns_sse_adapter(self) -> None:
        adapter = create_transport_adapter("sse", "http://localhost:8080/sse")
        assert isinstance(adapter, SSETransportAdapter)

    def test_http_returns_streamable_http_adapter(self) -> None:
        adapter = create_transport_adapter("http", "http://localhost:8080/mcp")
        assert isinstance(adapter, StreamableHTTPTransportAdapter)

    def test_unknown_transport_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Unknown transport type 'websocket'"):
            create_transport_adapter("websocket", "ws://localhost")  # type: ignore[arg-type]

    def test_error_lists_available_transports(self) -> None:
        with pytest.raises(ValueError, match="Available transports: http, sse, stdio"):
            create_transport_adapter("grpc", "localhost:50051")  # type: ignore[arg-type]

    def test_transport_options_forwarded_to_stdio(self) -> None:
        opts = {"env": {"FOO": "bar"}}
        adapter = create_transport_adapter("stdio", "python server.py", opts)
        assert isinstance(adapter, StdioTransportAdapter)
        assert adapter._transport_options == opts

    def test_transport_options_forwarded_to_sse(self) -> None:
        opts = {"headers": {"Authorization": "Bearer tok"}}
        adapter = create_transport_adapter("sse", "http://localhost/sse", opts)
        assert isinstance(adapter, SSETransportAdapter)
        assert adapter._transport_options == opts

    def test_transport_options_forwarded_to_http(self) -> None:
        opts = {"timeout": 60}
        adapter = create_transport_adapter("http", "http://localhost/mcp", opts)
        assert isinstance(adapter, StreamableHTTPTransportAdapter)
        assert adapter._transport_options == opts


# ---------------------------------------------------------------------------
# Adapter construction
# ---------------------------------------------------------------------------


class TestStdioAdapterConstruction:
    """Test StdioTransportAdapter initialisation."""

    def test_stores_command(self) -> None:
        adapter = StdioTransportAdapter(server_command="node server.js --port 3000")
        assert adapter._server_command == "node server.js --port 3000"

    def test_default_transport_options(self) -> None:
        adapter = StdioTransportAdapter(server_command="echo hi")
        assert adapter._transport_options == {}

    def test_cm_initially_none(self) -> None:
        adapter = StdioTransportAdapter(server_command="echo hi")
        assert adapter._cm is None


class TestSSEAdapterConstruction:
    """Test SSETransportAdapter initialisation."""

    def test_stores_url(self) -> None:
        adapter = SSETransportAdapter(url="http://localhost:8080/sse")
        assert adapter._url == "http://localhost:8080/sse"

    def test_default_transport_options(self) -> None:
        adapter = SSETransportAdapter(url="http://localhost/sse")
        assert adapter._transport_options == {}


class TestStreamableHTTPAdapterConstruction:
    """Test StreamableHTTPTransportAdapter initialisation."""

    def test_stores_url(self) -> None:
        adapter = StreamableHTTPTransportAdapter(url="http://localhost:8080/mcp")
        assert adapter._url == "http://localhost:8080/mcp"

    def test_default_transport_options(self) -> None:
        adapter = StreamableHTTPTransportAdapter(url="http://localhost/mcp")
        assert adapter._transport_options == {}


# ---------------------------------------------------------------------------
# Close when not connected (no-op safety)
# ---------------------------------------------------------------------------


class TestCloseWithoutConnect:
    """Calling close() before connect() should be a safe no-op."""

    @pytest.mark.asyncio
    async def test_stdio_close_noop(self) -> None:
        adapter = StdioTransportAdapter(server_command="echo hi")
        await adapter.close()  # should not raise

    @pytest.mark.asyncio
    async def test_sse_close_noop(self) -> None:
        adapter = SSETransportAdapter(url="http://localhost/sse")
        await adapter.close()

    @pytest.mark.asyncio
    async def test_http_close_noop(self) -> None:
        adapter = StreamableHTTPTransportAdapter(url="http://localhost/mcp")
        await adapter.close()
