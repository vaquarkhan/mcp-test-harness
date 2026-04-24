"""Server lifecycle management for the MCP Test Harness.

Manages starting, monitoring, and shutting down the MCP server under test.
Handles the MCP initialize handshake, startup timeouts, graceful shutdown
with a 10-second force-kill fallback, and background process monitoring.

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import sys
from dataclasses import dataclass
from typing import Any

from mcp_test_harness.config import HarnessConfig
from mcp_test_harness.transport import TransportAdapter, create_transport_adapter

logger = logging.getLogger(__name__)

# Lazy-loaded reference to mcp.ClientSession.  Assigned on first use in
# ``ServerLifecycleManager.start()`` so the module can be imported even
# when the ``mcp`` SDK is not installed.
_ClientSession: type | None = None


def _get_client_session_class() -> type:
    """Return ``mcp.ClientSession``, importing it on first call."""
    global _ClientSession  # noqa: PLW0603
    if _ClientSession is None:
        from mcp import ClientSession

        _ClientSession = ClientSession
    return _ClientSession

# Force-kill timeout in seconds (Requirement 1.5)
_FORCE_KILL_TIMEOUT = 10.0


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class StartupError(Exception):
    """Raised when the server fails to start or complete the MCP handshake."""


class ServerCrashedError(Exception):
    """Raised when the server process exits unexpectedly during a test run."""


# ---------------------------------------------------------------------------
# ManagedServer dataclass
# ---------------------------------------------------------------------------


@dataclass
class ManagedServer:
    """A running MCP server with its associated session and transport.

    Attributes
    ----------
    process:
        The subprocess handle for stdio servers (``anyio.abc.Process`` on most
        platforms), or ``None`` for remote (SSE / HTTP) servers.
    session:
        The active ``mcp.ClientSession`` connected to the server.
    transport:
        The transport adapter managing the underlying connection.
    capabilities:
        The server capabilities returned by the MCP initialize handshake.
    init_result:
        Raw object returned from ``session.initialize()`` for schema checks.
    """

    process: Any
    session: Any  # mcp.ClientSession
    transport: TransportAdapter
    capabilities: dict[str, Any]
    init_result: Any = None


# ---------------------------------------------------------------------------
# ServerLifecycleManager
# ---------------------------------------------------------------------------


class ServerLifecycleManager:
    """Manages the full lifecycle of an MCP server under test.

    Responsibilities:
    - Start the server process and establish a transport connection (Req 1.1, 1.2)
    - Perform the MCP initialize handshake with timeout (Req 1.3)
    - Graceful shutdown with 10s force-kill fallback (Req 1.4, 1.5)
    - Background monitoring for unexpected server exit (Req 1.6)
    """

    def __init__(self) -> None:
        self._monitor_task: asyncio.Task[None] | None = None

    # ------------------------------------------------------------------
    # start  (Requirements 1.1, 1.2, 1.3)
    # ------------------------------------------------------------------

    async def start(self, config: HarnessConfig) -> ManagedServer:
        """Start the server, create transport, and perform the MCP handshake.

        Parameters
        ----------
        config:
            The harness configuration containing server command, transport
            type, timeout, and transport options.

        Returns
        -------
        ManagedServer
            A fully initialised server ready for test execution.

        Raises
        ------
        StartupError
            If the server cannot be started, the transport fails to
            connect, or the MCP initialize handshake times out.
        """
        ClientSession = _get_client_session_class()

        # 1. Create the transport adapter (Req 1.1, 1.2)
        transport = create_transport_adapter(
            transport_type=config.transport,
            server_command=config.server_command,
            transport_options=config.transport_options,
        )

        # 2. Connect the transport -- yields (read_stream, write_stream)
        try:
            read_stream, write_stream = await transport.connect()
        except Exception as exc:
            raise StartupError(
                f"Failed to establish {config.transport} transport: {exc}"
            ) from exc

        # 3. Create a ClientSession and perform the initialize handshake
        #    with the configured timeout (Req 1.3).  Use __aenter__ / __aexit__
        #    so a failed ``initialize()`` does not leave the session half-open.
        session = ClientSession(read_stream, write_stream)

        init_result: Any = None
        session_entered = False
        try:
            await session.__aenter__()
            session_entered = True
            init_result = await asyncio.wait_for(
                session.initialize(),
                timeout=config.timeout,
            )
        except asyncio.TimeoutError:
            if session_entered:
                await self._safe_session_aexit(session, None, None, None)
            await self._safe_close_transport(transport)
            raise StartupError(
                f"MCP initialize handshake timed out after {config.timeout}s. "
                "Aborting test run."
            )
        except Exception as exc:
            if session_entered:
                await self._safe_session_aexit(session, *sys.exc_info())
            await self._safe_close_transport(transport)
            raise StartupError(
                f"MCP initialize handshake failed: {exc}"
            ) from exc

        # For assertions such as ``assert_protocol_version`` on harness-started sessions
        try:
            setattr(session, "_mcp_harness_init_result", init_result)
        except Exception:  # pragma: no cover
            pass  # pragma: no cover

        # 4. Extract capabilities from the handshake result
        capabilities = self._extract_capabilities(init_result)

        # 5. Subprocess handle (stdio) — required for crash monitoring and shutdown
        process = self._extract_process(transport)
        if config.transport == "stdio" and process is None:
            await self._safe_close_transport(transport)
            raise StartupError(
                "Stdio transport did not expose a subprocess handle after connect. "
                "Crash detection and clean shutdown need the server process; "
                "check StdioTransportAdapter and stdio_client_exposing_process."
            )

        server = ManagedServer(
            process=process,
            session=session,
            transport=transport,
            capabilities=capabilities,
            init_result=init_result,
        )

        logger.info(
            "Server started successfully (transport=%s, capabilities=%s)",
            config.transport,
            list(capabilities.keys()),
        )
        return server

    # ------------------------------------------------------------------
    # shutdown  (Requirements 1.4, 1.5)
    # ------------------------------------------------------------------

    async def shutdown(self, server: ManagedServer) -> None:
        """Gracefully shut down the server with a 10s force-kill timeout.

        Parameters
        ----------
        server:
            The managed server to shut down.
        """
        # Cancel the monitor task first
        if self._monitor_task is not None and not self._monitor_task.done():
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None

        # Close MCP session context (pairs with __aenter__ in ``start``)
        await self._safe_session_aexit(server.session, None, None, None)

        # Close the transport (sends any protocol-level shutdown)
        await self._safe_close_transport(server.transport)

        # If we have a subprocess, wait for it to exit gracefully,
        # then force-kill after _FORCE_KILL_TIMEOUT (Req 1.5)
        if server.process is not None:
            try:
                server.process.terminate()
                logger.debug("Sent SIGTERM to server process (pid=%s)", server.process.pid)
            except ProcessLookupError:
                # Already exited
                return

            try:
                await asyncio.wait_for(
                    server.process.wait(),
                    timeout=_FORCE_KILL_TIMEOUT,
                )
                logger.debug("Server process exited gracefully")
            except asyncio.TimeoutError:
                logger.warning(
                    "Server process (pid=%s) did not terminate within %ss, "
                    "force-killing",
                    server.process.pid,
                    _FORCE_KILL_TIMEOUT,
                )
                try:
                    server.process.kill()
                    await server.process.wait()
                except ProcessLookupError:
                    pass

    # ------------------------------------------------------------------
    # monitor  (Requirement 1.6)
    # ------------------------------------------------------------------

    async def monitor(self, server: ManagedServer) -> None:
        """Background task that detects unexpected server exit.

        This should be launched as an asyncio task. It watches the server
        process (stdio transport only) and raises :class:`ServerCrashedError`
        if the process exits while the test run is still in progress.

        For remote servers (SSE/HTTP) where ``server.process`` is ``None``,
        this method returns immediately -- there is no local process to watch.

        Parameters
        ----------
        server:
            The managed server to monitor.

        Raises
        ------
        ServerCrashedError
            If the server process exits unexpectedly.
        """
        if server.process is None:
            # Remote server -- nothing to monitor locally
            return

        return_code = await server.process.wait()
        # If we get here, the process exited while we were still monitoring
        raise ServerCrashedError(
            f"Server process exited unexpectedly with return code {return_code}"
        )

    def start_monitor(self, server: ManagedServer) -> asyncio.Task[None] | None:
        """Launch the monitor as a background asyncio task.

        Returns the task handle, or ``None`` if there is no process to
        monitor (remote servers).
        """
        if server.process is None:
            return None

        self._monitor_task = asyncio.create_task(
            self.monitor(server),
            name="mcp-server-monitor",
        )
        return self._monitor_task

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    async def _safe_session_aexit(
        session: Any,
        exc_type: Any,
        exc_val: Any,
        exc_tb: Any,
    ) -> None:
        """Call ``session.__aexit__`` if present (async or sync)."""
        aexit = getattr(session, "__aexit__", None)
        if aexit is None:
            return
        try:
            out = aexit(exc_type, exc_val, exc_tb)
            if inspect.isawaitable(out):
                await out
        except Exception:
            logger.debug("Error in session __aexit__ (ignored)", exc_info=True)

    @staticmethod
    def _extract_capabilities(init_result: Any) -> dict[str, Any]:
        """Extract a plain dict of capabilities from the handshake result."""
        if init_result is None:
            return {}
        # The MCP SDK returns an InitializeResult with a .capabilities attr
        caps = getattr(init_result, "capabilities", None)
        if caps is None:
            return {}
        # If capabilities is a pydantic model or dataclass, convert to dict
        if hasattr(caps, "model_dump"):
            return caps.model_dump(exclude_none=True)
        if hasattr(caps, "__dict__"):
            return {k: v for k, v in vars(caps).items() if v is not None}
        return {}

    @staticmethod
    def _extract_process(transport: TransportAdapter) -> Any:
        """Return the stdio subprocess handle from the transport adapter.

        Non-stdio transports do not use a local process — this is always
        ``None`` for them. For **stdio**, :meth:`start` raises
        :class:`StartupError` if this is ``None`` after connect; there is
        no alternate code path.
        """
        return getattr(transport, "_process", None)

    @staticmethod
    async def _safe_close_transport(transport: TransportAdapter) -> None:
        """Close the transport, swallowing any errors."""
        try:
            await transport.close()
        except Exception:
            logger.debug("Error closing transport (ignored)", exc_info=True)
