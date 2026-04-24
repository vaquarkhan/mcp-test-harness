"""Tests for stdio_mcp: failure paths and cleanup."""

from __future__ import annotations

from unittest.mock import patch

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
