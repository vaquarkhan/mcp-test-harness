#!/usr/bin/env python3
"""
Run many MCP assertion helpers against a *duck-typed* fake session (no real server).

This is the fastest way to see call shapes for: tool calls, resource/prompt
checks, list subset assertions, error paths, idempotency, latency, protocol
version, and snapshots.

Run:
    python examples/assertions_async_demo.py

Prerequisites:
    pip install -e "."
"""
from __future__ import annotations

import asyncio
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from mcp_test_harness.assertions import (
    assert_capabilities,
    assert_invalid_tool,
    assert_latency,
    assert_prompt,
    assert_protocol_version,
    assert_resource_list,
    assert_resource_read,
    assert_snapshot,
    assert_tool_call,
    assert_tool_call_validates_input,
    assert_tool_idempotent,
    assert_tool_list,
    assert_tool_rejects,
    assert_tool_schema,
)

# -- minimal stand-ins (same idea as the harness unit tests) -----------------


@dataclass
class FakeContent:
    text: str = ""
    isError: bool = False


@dataclass
class FakeToolResult:
    content: list[FakeContent] = field(default_factory=list)


@dataclass
class FakeResourceContent:
    text: str = ""
    mimeType: str = "text/plain"


@dataclass
class FakeResourceResult:
    contents: list[FakeResourceContent] = field(default_factory=list)


@dataclass
class FakeMessage:
    role: str = "user"
    content: str = ""


@dataclass
class FakePromptResult:
    messages: list[FakeMessage] = field(default_factory=list)


@dataclass
class FakeTool:
    name: str
    inputSchema: dict[str, Any] = field(
        default_factory=lambda: {"type": "object", "properties": {}}
    )


@dataclass
class FakeToolListResult:
    tools: list[FakeTool] = field(default_factory=list)


@dataclass
class FakeResource:
    uri: str


@dataclass
class FakeResourceListResult:
    resources: list[FakeResource] = field(default_factory=list)


class DemoSession:
    """Duck-typed fake MCP session for the demo (no I/O, no real server)."""

    def __init__(self) -> None:
        self.server_capabilities: dict[str, Any] = {
            "tools": True,
            "resources": True,
        }
        self._mcp_harness_init_result = SimpleNamespace(
            protocolVersion="2024-11-05",
        )
        self._tool_list = FakeToolListResult(
            tools=[
                FakeTool(
                    "echo",
                    {
                        "type": "object",
                        "properties": {"text": {"type": "string"}},
                    },
                )
            ],
        )
        self._res_list = FakeResourceListResult(
            resources=[FakeResource("file://demo/notes.txt")],
        )

    async def list_tools(self) -> FakeToolListResult:
        return self._tool_list

    async def list_resources(self) -> FakeResourceListResult:
        return self._res_list

    async def read_resource(self, uri: str) -> FakeResourceResult:
        return FakeResourceResult(
            contents=[FakeResourceContent(text="hello resource", mimeType="text/plain")],
        )

    async def get_prompt(
        self, name: str, arguments: dict[str, str] | None = None
    ) -> FakePromptResult:
        return FakePromptResult(
            messages=[FakeMessage(role="user", content="do the thing")],
        )

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> FakeToolResult:
        names = {t.name for t in self._tool_list.tools}
        if name not in names:
            return FakeToolResult(
                content=[FakeContent(text="Unknown tool", isError=True)]
            )
        if name == "echo" and arguments.get("bad"):
            return FakeToolResult(
                content=[FakeContent(text="invalid payload", isError=True)]
            )
        if name == "echo":
            return FakeToolResult(
                content=[
                    FakeContent(text=str(arguments.get("text", "ok")), isError=False)
                ]
            )
        return FakeToolResult(
            content=[FakeContent(text="error", isError=True)]
        )


async def _run() -> None:
    s = DemoSession()
    print("1) assert_tool_call")
    r = await assert_tool_call(s, "echo", {"text": "hi"})
    assert r.content[0].text == "hi"

    print("2) assert_resource_read (exact first-block text + MIME)")
    await assert_resource_read(
        s,
        "file://demo/notes.txt",
        expected_content="hello resource",
        expected_mime_type="text/plain",
    )

    print("3) assert_prompt")
    await assert_prompt(s, "p1", expected_messages=[{"role": "user", "content": "do the thing"}])

    print("4) assert_capabilities")
    await assert_capabilities(s, {"tools": True})

    print("5) assert_tool_list / assert_resource_list")
    await assert_tool_list(s, ["echo"])
    await assert_resource_list(s, ["file://demo/notes.txt"])

    print("6) assert_tool_rejects (explicit error from server)")
    await assert_tool_rejects(s, "echo", {"bad": True}, error_substring="invalid")

    print("7) assert_invalid_tool (name not in catalog)")
    await assert_invalid_tool(s, "nope")

    print("8) assert_tool_schema")
    await assert_tool_schema(
        s,
        "echo",
        {
            "type": "object",
            "properties": {"text": {"type": "string"}},
        },
    )

    print("9) assert_protocol_version")
    await assert_protocol_version(s, "2024-11-05")

    print("10) assert_tool_idempotent")
    await assert_tool_idempotent(s, "echo", {"text": "x"}, runs=3)

    print("11) assert_tool_call_validates_input")
    await assert_tool_call_validates_input(
        s, "echo", {"bad": True}, expected_error_substring="invalid"
    )

    print("12) assert_latency (single run)")
    await assert_latency(
        s,
        "echo",
        {"text": "ping"},
        max_ms=5_000.0,
        runs=1,
        aggregate="max",
    )

    print("13) assert_snapshot (writes to a temp file's __snapshots__ dir)")
    with tempfile.TemporaryDirectory() as tmp:
        tdir = Path(tmp)
        tfile = tdir / "test_demo.py"
        tfile.write_text("# demo\n", encoding="utf-8")
        (tdir / "__snapshots__").mkdir(exist_ok=True)
        await assert_snapshot(
            {"a": 1, "b": "stable"},
            "demo",
            test_file=tfile,
            update=True,
        )
        await assert_snapshot(
            {"a": 1, "b": "stable"},
            "demo",
            test_file=tfile,
            update=False,
        )
    print("    snapshot round-trip OK under temp dir")

    print("\nAll assertion demos passed.")


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
