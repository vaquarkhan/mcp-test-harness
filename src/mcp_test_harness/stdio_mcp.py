"""Stdio transport with exposed subprocess handle (anyio) for crash monitoring.

Vendored from ``mcp.client.stdio.stdio_client``; yields ``(read, write, process)``
so :class:`StdioTransportAdapter` can set ``_process`` for lifecycle monitoring.
"""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from typing import TextIO

import anyio
import anyio.lowlevel
import mcp.types as types
from anyio.abc import Process
from anyio.streams.text import TextReceiveStream
from mcp.client.stdio import (
    PROCESS_TERMINATION_TIMEOUT,
    StdioServerParameters,
    get_default_environment,
    _create_platform_compatible_process,  # noqa: SLF001
    _get_executable_command,  # noqa: SLF001
    _terminate_process_tree,  # noqa: SLF001
)
from mcp.shared.message import SessionMessage

logger = logging.getLogger(__name__)


@asynccontextmanager
async def stdio_client_exposing_process(
    server: StdioServerParameters, errlog: TextIO = sys.stderr
):
    """Like ``mcp.client.stdio.stdio_client`` but also yields the server ``process``."""
    read_stream_writer, read_stream = anyio.create_memory_object_stream(0)
    write_stream, write_stream_reader = anyio.create_memory_object_stream(0)

    process: Process

    try:
        command = _get_executable_command(server.command)
        process = await _create_platform_compatible_process(
            command=command,
            args=server.args,
            env=(
                {**get_default_environment(), **server.env}
                if server.env is not None
                else get_default_environment()
            ),
            errlog=errlog,
            cwd=server.cwd,
        )
    except OSError:
        await read_stream.aclose()
        await write_stream.aclose()
        await read_stream_writer.aclose()
        await write_stream_reader.aclose()
        raise

    async def stdout_reader() -> None:
        assert process.stdout, "Opened process is missing stdout"

        try:
            async with read_stream_writer:
                buffer = ""
                async for chunk in TextReceiveStream(
                    process.stdout,
                    encoding=server.encoding,
                    errors=server.encoding_error_handler,
                ):
                    lines = (buffer + chunk).split("\n")
                    buffer = lines.pop()

                    for line in lines:
                        try:
                            message = types.JSONRPCMessage.model_validate_json(line)
                        except Exception as exc:  # pragma: no cover
                            logger.exception(
                                "Failed to parse JSONRPC message from server"
                            )
                            await read_stream_writer.send(exc)
                            continue

                        session_message = SessionMessage(message)
                        await read_stream_writer.send(session_message)
        except anyio.ClosedResourceError:  # pragma: no cover
            await anyio.lowlevel.checkpoint()

    async def stdin_writer() -> None:
        assert process.stdin, "Opened process is missing stdin"

        try:
            async with write_stream_reader:
                async for session_message in write_stream_reader:
                    j = session_message.message.model_dump_json(
                        by_alias=True, exclude_none=True
                    )
                    await process.stdin.send(
                        (j + "\n").encode(
                            encoding=server.encoding,
                            errors=server.encoding_error_handler,
                        )
                    )
        except anyio.ClosedResourceError:  # pragma: no cover
            await anyio.lowlevel.checkpoint()

    async with (
        anyio.create_task_group() as tg,
        process,
    ):
        tg.start_soon(stdout_reader)
        tg.start_soon(stdin_writer)
        try:
            yield read_stream, write_stream, process
        finally:
            if process.stdin:  # pragma: no branch
                try:
                    await process.stdin.aclose()
                except Exception:  # pragma: no cover
                    pass

            try:
                with anyio.fail_after(PROCESS_TERMINATION_TIMEOUT):
                    await process.wait()
            except TimeoutError:
                await _terminate_process_tree(process)
            except ProcessLookupError:  # pragma: no cover
                pass
            await read_stream.aclose()
            await write_stream.aclose()
            await read_stream_writer.aclose()
            await write_stream_reader.aclose()
