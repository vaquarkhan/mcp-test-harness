"""Minimal FastMCP server used by harness dogfood e2e tests."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

m = FastMCP("harness-dogfood")


@m.tool()
def echo(text: str) -> str:
    """Echo text back."""
    return text


if __name__ == "__main__":
    m.run()
