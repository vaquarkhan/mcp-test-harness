"""Transport adapters for the MCP Test Harness.

Wraps the MCP Python SDK transport context managers behind a unified
:class:`TransportAdapter` protocol so that the lifecycle manager and
test executor can work with any transport type interchangeably.

Requirements: 11.1, 11.2, 11.3, 11.4, 11.5
"""

from __future__ import annotations

import contextlib
import logging
import os
import shlex
from typing import Any, Protocol, runtime_checkable

from mcp_test_harness.stdio_mcp import stdio_client_exposing_process

from mcp_test_harness.models import TransportType

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class TransportAdapter(Protocol):
    """Unified interface for MCP transport connections.

    Implementations wrap the MCP SDK's async context-manager transports
    and expose a simple ``connect`` / ``close`` pair.
    """

    async def connect(self) -> tuple[Any, Any]:
        """Establish the transport connection.

        Returns a ``(read_stream, write_stream)`` tuple suitable for
        passing to ``mcp.ClientSession``.
        """
        ...  # pragma: no cover

    async def close(self) -> None:
        """Tear down the transport connection and release resources."""
        ...  # pragma: no cover


# ---------------------------------------------------------------------------
# Stdio adapter  (Requirement 11.1)
# ---------------------------------------------------------------------------


class StdioTransportAdapter:
    """Wraps ``mcp.client.stdio.stdio_client`` for subprocess-based servers.

    Parameters
    ----------
    server_command:
        The shell command used to spawn the MCP server process.
    transport_options:
        Extra keyword arguments forwarded to the SDK's
        ``StdioServerParameters`` (e.g. ``env``, ``cwd``).
    """

    def __init__(
        self,
        server_command: str,
        transport_options: dict[str, Any] | None = None,
    ) -> None:
        self._server_command = server_command
        self._transport_options = transport_options or {}
        self._cm: contextlib.AsyncExitStack | None = None
        # Populated in connect() for stdio — used by ServerLifecycleManager monitoring
        self._process: Any = None

    async def connect(self) -> tuple[Any, Any]:
        from mcp.client.stdio import StdioServerParameters

        # POSIX=False on Windows preserves backslashes in paths; POSIX=True elsewhere
        parts = shlex.split(self._server_command, posix=os.name != "nt")
        if not parts:
            raise ValueError("server_command is empty or contains no arguments")
        command = parts[0]
        args = parts[1:]

        params = StdioServerParameters(
            command=command,
            args=args,
            **self._transport_options,
        )

        self._cm = contextlib.AsyncExitStack()
        read_stream, write_stream, self._process = await self._cm.enter_async_context(
            stdio_client_exposing_process(params),
        )
        return read_stream, write_stream

    async def close(self) -> None:
        if self._cm is not None:
            await self._cm.aclose()
            self._cm = None
        self._process = None


# ---------------------------------------------------------------------------
# SSE adapter  (Requirement 11.2)
# ---------------------------------------------------------------------------


class SSETransportAdapter:
    """Wraps ``mcp.client.sse.sse_client`` for SSE-based servers.

    Parameters
    ----------
    url:
        The HTTP(S) URL of the SSE endpoint exposed by the MCP server.
    transport_options:
        Extra keyword arguments forwarded to ``sse_client``.
    """

    def __init__(
        self,
        url: str,
        transport_options: dict[str, Any] | None = None,
    ) -> None:
        self._url = url
        self._transport_options = transport_options or {}
        self._cm: contextlib.AsyncExitStack | None = None

    async def connect(self) -> tuple[Any, Any]:
        from mcp.client.sse import sse_client

        self._cm = contextlib.AsyncExitStack()
        read_stream, write_stream = await self._cm.enter_async_context(
            sse_client(self._url, **self._transport_options),
        )
        return read_stream, write_stream

    async def close(self) -> None:
        if self._cm is not None:
            await self._cm.aclose()
            self._cm = None


# ---------------------------------------------------------------------------
# Streamable HTTP adapter  (Requirement 11.3)
# ---------------------------------------------------------------------------


class StreamableHTTPTransportAdapter:
    """Wraps ``mcp.client.streamable_http.streamablehttp_client``.

    Parameters
    ----------
    url:
        The HTTP(S) URL of the streamable HTTP endpoint.
    transport_options:
        Extra keyword arguments forwarded to ``streamablehttp_client``.
    """

    def __init__(
        self,
        url: str,
        transport_options: dict[str, Any] | None = None,
    ) -> None:
        self._url = url
        self._transport_options = transport_options or {}
        self._cm: contextlib.AsyncExitStack | None = None

    async def connect(self) -> tuple[Any, Any]:
        from mcp.client.streamable_http import streamablehttp_client

        self._cm = contextlib.AsyncExitStack()
        # streamablehttp_client yields (read, write, session_id); we only
        # need the first two for the ClientSession interface.
        read_stream, write_stream, _session_id = (
            await self._cm.enter_async_context(
                streamablehttp_client(self._url, **self._transport_options),
            )
        )
        return read_stream, write_stream

    async def close(self) -> None:
        if self._cm is not None:
            await self._cm.aclose()
            self._cm = None


# ---------------------------------------------------------------------------
# Factory  (Requirements 11.4, 11.5)
# ---------------------------------------------------------------------------

# Registry of built-in transport types.  Plugins can extend this at runtime
# via the plugin registry's ``add_transport`` hook.
_BUILTIN_TRANSPORTS: dict[str, type] = {
    "stdio": StdioTransportAdapter,
    "sse": SSETransportAdapter,
    "http": StreamableHTTPTransportAdapter,
}


def create_transport_adapter(
    transport_type: TransportType,
    server_command: str,
    transport_options: dict[str, Any] | None = None,
) -> TransportAdapter:
    """Create a :class:`TransportAdapter` for the given *transport_type*.

    Parameters
    ----------
    transport_type:
        One of ``"stdio"``, ``"sse"``, or ``"http"``.
    server_command:
        The server command string (used by stdio) or URL (used by
        SSE / streamable HTTP).
    transport_options:
        Additional options forwarded to the underlying adapter.

    Returns
    -------
    TransportAdapter
        A concrete adapter instance ready to ``connect()``.

    Raises
    ------
    ValueError
        If *transport_type* is not a recognised transport.
    """
    if transport_type not in _BUILTIN_TRANSPORTS:
        available = ", ".join(sorted(_BUILTIN_TRANSPORTS))
        raise ValueError(
            f"Unknown transport type '{transport_type}'. "
            f"Available transports: {available}"
        )

    adapter_cls = _BUILTIN_TRANSPORTS[transport_type]

    if transport_type == "stdio":
        return adapter_cls(
            server_command=server_command,
            transport_options=transport_options,
        )

    # SSE and HTTP adapters take a URL rather than a command.
    return adapter_cls(
        url=server_command,
        transport_options=transport_options,
    )
