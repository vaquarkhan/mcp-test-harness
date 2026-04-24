"""Integration: real subprocess via stdio_client_exposing_process (stdio_mcp)."""

from __future__ import annotations

import sys
from pathlib import Path

import anyio
import pytest
from mcp.client.stdio import StdioServerParameters

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
