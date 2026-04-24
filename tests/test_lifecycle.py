"""Unit tests for mcp_test_harness.lifecycle."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_test_harness.config import HarnessConfig
from mcp_test_harness.lifecycle import (
    ManagedServer,
    ServerCrashedError,
    ServerLifecycleManager,
    StartupError,
    _FORCE_KILL_TIMEOUT,
)


# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------


def _make_config(**overrides: Any) -> HarnessConfig:
    """Create a HarnessConfig with sensible defaults for testing."""
    defaults = {
        "server_command": "python fake_server.py",
        "transport": "stdio",
        "timeout": 5.0,
    }
    defaults.update(overrides)
    return HarnessConfig(**defaults)


def _make_mock_transport(read: Any = None, write: Any = None) -> AsyncMock:
    """Create a mock TransportAdapter."""
    transport = AsyncMock()
    transport.connect = AsyncMock(return_value=(read or MagicMock(), write or MagicMock()))
    transport.close = AsyncMock()
    # Real stdio exposes a process handle; avoid AsyncMock’s auto children so
    # ``_extract_process`` does not get a truthy fake ``_process`` by default.
    transport._process = _make_mock_process()
    return transport


def _make_mock_session(capabilities: Any = None) -> MagicMock:
    """Create a mock ClientSession that supports async context manager."""
    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)

    init_result = MagicMock()
    if capabilities is not None:
        init_result.capabilities = capabilities
    else:
        init_result.capabilities = None
    session.initialize = AsyncMock(return_value=init_result)
    return session


def _make_mock_process(
    return_code: int = 0,
    wait_hangs: bool = False,
) -> MagicMock:
    """Create a mock asyncio.subprocess.Process."""
    process = MagicMock()
    process.pid = 12345

    if wait_hangs:
        # Simulate a process that never exits (for force-kill testing)
        async def hang_forever() -> int:
            await asyncio.sleep(999)
            return return_code

        process.wait = hang_forever
    else:
        process.wait = AsyncMock(return_value=return_code)

    process.terminate = MagicMock()
    process.kill = MagicMock()
    return process


# ---------------------------------------------------------------------------
# ManagedServer dataclass
# ---------------------------------------------------------------------------


class TestManagedServer:
    """Tests for the ManagedServer dataclass."""

    def test_creation_with_all_fields(self) -> None:
        server = ManagedServer(
            process=None,
            session=MagicMock(),
            transport=MagicMock(),
            capabilities={"tools": True},
        )
        assert server.process is None
        assert server.capabilities == {"tools": True}

    def test_creation_with_process(self) -> None:
        proc = MagicMock()
        server = ManagedServer(
            process=proc,
            session=MagicMock(),
            transport=MagicMock(),
            capabilities={},
        )
        assert server.process is proc


# ---------------------------------------------------------------------------
# Error classes
# ---------------------------------------------------------------------------


class TestErrorClasses:
    """Tests for StartupError and ServerCrashedError."""

    def test_startup_error_message(self) -> None:
        err = StartupError("handshake failed")
        assert str(err) == "handshake failed"

    def test_server_crashed_error_message(self) -> None:
        err = ServerCrashedError("exit code 1")
        assert str(err) == "exit code 1"

    def test_startup_error_is_exception(self) -> None:
        assert issubclass(StartupError, Exception)

    def test_server_crashed_error_is_exception(self) -> None:
        assert issubclass(ServerCrashedError, Exception)


# ---------------------------------------------------------------------------
# ServerLifecycleManager.start()
# ---------------------------------------------------------------------------


class TestStart:
    """Tests for ServerLifecycleManager.start()."""

    @pytest.mark.asyncio
    async def test_successful_start(self) -> None:
        """A successful start returns a ManagedServer with session and capabilities."""
        config = _make_config()
        manager = ServerLifecycleManager()

        mock_transport = _make_mock_transport()
        mock_session = _make_mock_session()
        mock_cls = MagicMock(return_value=mock_session)

        with (
            patch(
                "mcp_test_harness.lifecycle.create_transport_adapter",
                return_value=mock_transport,
            ),
            patch(
                "mcp_test_harness.lifecycle._get_client_session_class",
                return_value=mock_cls,
            ),
        ):
            server = await manager.start(config)

        assert isinstance(server, ManagedServer)
        assert server.session is mock_session
        assert server.transport is mock_transport
        mock_transport.connect.assert_awaited_once()
        mock_session.initialize.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_start_transport_failure_raises_startup_error(self) -> None:
        """If the transport fails to connect, StartupError is raised."""
        config = _make_config()
        manager = ServerLifecycleManager()

        mock_transport = AsyncMock()
        mock_transport.connect = AsyncMock(side_effect=ConnectionError("refused"))

        with (
            patch(
                "mcp_test_harness.lifecycle.create_transport_adapter",
                return_value=mock_transport,
            ),
            pytest.raises(StartupError, match="Failed to establish stdio transport"),
        ):
            await manager.start(config)

    @pytest.mark.asyncio
    async def test_start_handshake_timeout_raises_startup_error(self) -> None:
        """If the MCP handshake times out, StartupError is raised (Req 1.3)."""
        config = _make_config(timeout=0.1)
        manager = ServerLifecycleManager()

        mock_transport = _make_mock_transport()

        # Session that hangs during initialize
        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        async def slow_init() -> None:
            await asyncio.sleep(10)

        mock_session.initialize = slow_init
        mock_cls = MagicMock(return_value=mock_session)

        with (
            patch(
                "mcp_test_harness.lifecycle.create_transport_adapter",
                return_value=mock_transport,
            ),
            patch(
                "mcp_test_harness.lifecycle._get_client_session_class",
                return_value=mock_cls,
            ),
            pytest.raises(StartupError, match="timed out"),
        ):
            await manager.start(config)

        # Transport should be cleaned up on timeout
        mock_transport.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_start_handshake_exception_raises_startup_error(self) -> None:
        """If the MCP handshake raises, StartupError wraps it."""
        config = _make_config()
        manager = ServerLifecycleManager()

        mock_transport = _make_mock_transport()
        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.initialize = AsyncMock(side_effect=RuntimeError("protocol error"))
        mock_cls = MagicMock(return_value=mock_session)

        with (
            patch(
                "mcp_test_harness.lifecycle.create_transport_adapter",
                return_value=mock_transport,
            ),
            patch(
                "mcp_test_harness.lifecycle._get_client_session_class",
                return_value=mock_cls,
            ),
            pytest.raises(StartupError, match="handshake failed"),
        ):
            await manager.start(config)

        mock_transport.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_start_extracts_capabilities_from_model_dump(self) -> None:
        """Capabilities are extracted via model_dump when available."""
        config = _make_config()
        manager = ServerLifecycleManager()

        mock_transport = _make_mock_transport()

        caps = MagicMock()
        caps.model_dump = MagicMock(return_value={"tools": {"listChanged": True}})
        mock_session = _make_mock_session(capabilities=caps)
        mock_cls = MagicMock(return_value=mock_session)

        with (
            patch(
                "mcp_test_harness.lifecycle.create_transport_adapter",
                return_value=mock_transport,
            ),
            patch(
                "mcp_test_harness.lifecycle._get_client_session_class",
                return_value=mock_cls,
            ),
        ):
            server = await manager.start(config)

        assert server.capabilities == {"tools": {"listChanged": True}}

    @pytest.mark.asyncio
    async def test_start_stdio_fails_without_subprocess_handle(self) -> None:
        """Stdio must expose a process for monitoring and clean shutdown (Req 1.6)."""
        config = _make_config()
        manager = ServerLifecycleManager()
        mock_transport = _make_mock_transport()
        mock_transport._process = None
        mock_session = _make_mock_session()
        mock_cls = MagicMock(return_value=mock_session)

        with (
            patch(
                "mcp_test_harness.lifecycle.create_transport_adapter",
                return_value=mock_transport,
            ),
            patch(
                "mcp_test_harness.lifecycle._get_client_session_class",
                return_value=mock_cls,
            ),
            pytest.raises(StartupError, match="subprocess handle"),
        ):
            await manager.start(config)
        mock_transport.close.assert_awaited_once()


# ---------------------------------------------------------------------------
# ServerLifecycleManager.shutdown()
# ---------------------------------------------------------------------------


class TestShutdown:
    """Tests for ServerLifecycleManager.shutdown()."""

    @pytest.mark.asyncio
    async def test_graceful_shutdown_no_process(self) -> None:
        """Shutdown of a remote server (no process) just closes transport."""
        manager = ServerLifecycleManager()
        mock_transport = AsyncMock()
        mock_transport.close = AsyncMock()

        server = ManagedServer(
            process=None,
            session=MagicMock(),
            transport=mock_transport,
            capabilities={},
        )

        await manager.shutdown(server)
        mock_transport.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_graceful_shutdown_with_process(self) -> None:
        """Shutdown terminates the process and waits for exit (Req 1.4)."""
        manager = ServerLifecycleManager()
        mock_transport = AsyncMock()
        mock_transport.close = AsyncMock()
        mock_process = _make_mock_process(return_code=0)

        server = ManagedServer(
            process=mock_process,
            session=MagicMock(),
            transport=mock_transport,
            capabilities={},
        )

        await manager.shutdown(server)

        mock_process.terminate.assert_called_once()
        mock_transport.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_force_kill_after_timeout(self) -> None:
        """If process doesn't exit within 10s, it gets force-killed (Req 1.5)."""
        manager = ServerLifecycleManager()
        mock_transport = AsyncMock()
        mock_transport.close = AsyncMock()

        # Process that hangs on wait()
        mock_process = MagicMock()
        mock_process.pid = 99999

        call_count = 0

        async def slow_then_fast() -> int:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call (after terminate) -- hang to trigger timeout
                await asyncio.sleep(999)
            # Second call (after kill) -- return immediately
            return -9

        mock_process.wait = slow_then_fast
        mock_process.terminate = MagicMock()
        mock_process.kill = MagicMock()

        server = ManagedServer(
            process=mock_process,
            session=MagicMock(),
            transport=mock_transport,
            capabilities={},
        )

        # Patch the force-kill timeout to be very short for testing
        with patch("mcp_test_harness.lifecycle._FORCE_KILL_TIMEOUT", 0.1):
            await manager.shutdown(server)

        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_cancels_monitor_task(self) -> None:
        """Shutdown cancels any running monitor task."""
        manager = ServerLifecycleManager()

        # Create a fake monitor task
        async def fake_monitor() -> None:
            await asyncio.sleep(999)

        manager._monitor_task = asyncio.create_task(fake_monitor())

        mock_transport = AsyncMock()
        mock_transport.close = AsyncMock()

        server = ManagedServer(
            process=None,
            session=MagicMock(),
            transport=mock_transport,
            capabilities={},
        )

        await manager.shutdown(server)
        assert manager._monitor_task is None

    @pytest.mark.asyncio
    async def test_shutdown_handles_already_exited_process(self) -> None:
        """Shutdown handles ProcessLookupError when process already exited."""
        manager = ServerLifecycleManager()
        mock_transport = AsyncMock()
        mock_transport.close = AsyncMock()

        mock_process = MagicMock()
        mock_process.pid = 11111
        mock_process.terminate = MagicMock(side_effect=ProcessLookupError)

        server = ManagedServer(
            process=mock_process,
            session=MagicMock(),
            transport=mock_transport,
            capabilities={},
        )

        # Should not raise
        await manager.shutdown(server)

    @pytest.mark.asyncio
    async def test_shutdown_transport_error_swallowed(self) -> None:
        """Transport close errors are swallowed during shutdown."""
        manager = ServerLifecycleManager()
        mock_transport = AsyncMock()
        mock_transport.close = AsyncMock(side_effect=RuntimeError("close failed"))

        server = ManagedServer(
            process=None,
            session=MagicMock(),
            transport=mock_transport,
            capabilities={},
        )

        # Should not raise
        await manager.shutdown(server)


# ---------------------------------------------------------------------------
# ServerLifecycleManager.monitor()
# ---------------------------------------------------------------------------


class TestMonitor:
    """Tests for ServerLifecycleManager.monitor()."""

    @pytest.mark.asyncio
    async def test_monitor_returns_immediately_for_remote_server(self) -> None:
        """Monitor is a no-op for servers without a process (Req 1.6)."""
        manager = ServerLifecycleManager()
        server = ManagedServer(
            process=None,
            session=MagicMock(),
            transport=MagicMock(),
            capabilities={},
        )
        # Should return immediately without error
        await manager.monitor(server)

    @pytest.mark.asyncio
    async def test_monitor_raises_on_unexpected_exit(self) -> None:
        """Monitor raises ServerCrashedError when process exits (Req 1.6)."""
        manager = ServerLifecycleManager()
        mock_process = _make_mock_process(return_code=1)

        server = ManagedServer(
            process=mock_process,
            session=MagicMock(),
            transport=MagicMock(),
            capabilities={},
        )

        with pytest.raises(ServerCrashedError, match="return code 1"):
            await manager.monitor(server)

    @pytest.mark.asyncio
    async def test_start_monitor_returns_task(self) -> None:
        """start_monitor returns an asyncio.Task for stdio servers."""
        manager = ServerLifecycleManager()

        # Process that waits a bit then exits
        mock_process = MagicMock()
        mock_process.pid = 42

        async def wait_then_exit() -> int:
            await asyncio.sleep(0.5)
            return 1

        mock_process.wait = wait_then_exit

        server = ManagedServer(
            process=mock_process,
            session=MagicMock(),
            transport=MagicMock(),
            capabilities={},
        )

        task = manager.start_monitor(server)
        assert task is not None
        assert isinstance(task, asyncio.Task)

        # Clean up
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, ServerCrashedError):
            pass

    @pytest.mark.asyncio
    async def test_start_monitor_returns_none_for_remote(self) -> None:
        """start_monitor returns None for remote servers (no process)."""
        manager = ServerLifecycleManager()
        server = ManagedServer(
            process=None,
            session=MagicMock(),
            transport=MagicMock(),
            capabilities={},
        )

        task = manager.start_monitor(server)
        assert task is None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


class TestHelpers:
    """Tests for internal helper methods."""

    def test_extract_capabilities_none_result(self) -> None:
        result = ServerLifecycleManager._extract_capabilities(None)
        assert result == {}

    def test_extract_capabilities_no_caps_attr(self) -> None:
        result = MagicMock(spec=[])  # no attributes
        caps = ServerLifecycleManager._extract_capabilities(result)
        assert caps == {}

    def test_extract_capabilities_with_dict_attr(self) -> None:
        """Capabilities object with __dict__ but no model_dump."""

        class SimpleCaps:
            def __init__(self) -> None:
                self.tools = True
                self.resources = None

        result = MagicMock()
        result.capabilities = SimpleCaps()
        caps = ServerLifecycleManager._extract_capabilities(result)
        assert caps == {"tools": True}

    def test_extract_process_returns_none_for_non_stdio(self) -> None:
        transport = MagicMock(spec=[])
        result = ServerLifecycleManager._extract_process(transport)
        assert result is None

    def test_force_kill_timeout_value(self) -> None:
        assert _FORCE_KILL_TIMEOUT == 10.0
