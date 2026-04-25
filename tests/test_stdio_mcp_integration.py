"""Integration: real subprocess via stdio_client_exposing_process (stdio_mcp)."""

from __future__ import annotations

import sys
from pathlib import Path

import anyio
import pytest
import mcp.types as types
from mcp.client.stdio import StdioServerParameters
from mcp.shared.message import SessionMessage

from mcp_test_harness.stdio_mcp import stdio_client_exposing_process

_MINI_SERVER = """\
from mcp.server.fastmcp import FastMCP
m = FastMCP("harness_stdio_it")
if __name__ == "__main__":
    m.run()
"""


@pytest.mark.asyncio
async def test_stdio_client_exposing_process_starts_minimal_mcp_subprocess(
    tmp_path: Path,
) -> None:
    script = tmp_path / "mcp_s.py"
    script.write_text(_MINI_SERVER, encoding="utf-8")
    p = StdioServerParameters(command=sys.executable, args=[str(script)])
    with anyio.fail_after(15):
        async with stdio_client_exposing_process(p) as (_r, _w, proc):
            assert proc is not None
            pid = getattr(proc, "pid", None)
            assert pid is not None and pid != 0


@pytest.mark.asyncio
async def test_stdio_client_reads_and_writes_jsonrpc_messages(tmp_path: Path) -> None:
    script = tmp_path / "stdio_roundtrip.py"
    script.write_text(
        "import sys, time\n"
        'print(\'{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"ping\",\"params\":{}}\', flush=True)\n'
        "sys.stdin.readline()\n"
        "time.sleep(0.05)\n",
        encoding="utf-8",
    )
    p = StdioServerParameters(command=sys.executable, args=[str(script)])
    with anyio.fail_after(10):
        async with stdio_client_exposing_process(p) as (read_stream, write_stream, _proc):
            msg = await read_stream.receive()
            assert isinstance(msg, SessionMessage)
            outbound = types.JSONRPCMessage.model_validate(
                {"jsonrpc": "2.0", "id": 2, "method": "pong", "params": {}}
            )
            await write_stream.send(SessionMessage(outbound))
