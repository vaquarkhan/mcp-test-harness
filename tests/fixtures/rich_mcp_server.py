"""Rich FastMCP fixture for seam / dogfood e2e tests.

Exercises tools, resources, prompts, MCP isError, and a slow path so
coverage maps, README contracts, and record round-trips are meaningful.
"""

from __future__ import annotations

import time

from mcp.server.fastmcp import FastMCP

m = FastMCP("harness-seam-rich")


@m.tool()
def echo(text: str) -> str:
    """Echo text back."""
    return text


@m.tool()
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b


@m.tool()
def boom(reason: str = "fail") -> str:
    """Always returns an MCP tool error (isError)."""
    raise ValueError(f"boom: {reason}")


@m.tool()
def slow(ms: int = 50) -> str:
    """Sleep briefly then return (for latency/throughput smoke)."""
    time.sleep(max(0, ms) / 1000.0)
    return f"slept-{ms}"


@m.resource("seam://greeting")
def greeting() -> str:
    """A simple resource for assert_resource_read."""
    return "hello-from-seam"


@m.prompt()
def welcome(name: str = "world") -> str:
    """A simple prompt for assert_prompt."""
    return f"Welcome, {name}!"


if __name__ == "__main__":
    m.run()
