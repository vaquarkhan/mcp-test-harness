"""Suite A: semantic egress quarantine + known covert-encoding capacity tests.

Deterministic CI-gated path only (recorded-verdict / fixture sessions).
Live evaluator quality belongs under ``semantic_live`` / ``adaptive`` markers
and must not gate PRs. Covert tests cover known encodings only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace

import pytest

from mcp_test_harness.assertions import MCPAssertionError
from mcp_test_harness.security_payloads import (
    AISI_MAINTAINER_PRESSURE_PAYLOAD,
    BENIGN_EGRESS_CONTROLS,
    COVERT_CHANNEL_PAYLOADS,
    SOCIAL_ENGINEERING_PAYLOADS,
    assert_covert_channel_neutralized,
    assert_egress_allowed,
    assert_egress_quarantined,
    assert_general_exec_tools_absent,
)


@dataclass
class Content:
    text: str = ""
    isError: bool = False


@dataclass
class ToolResult:
    content: list[Content] = field(default_factory=list)
    isError: bool = False


class RecordedEgressSession:
    """Fixture server: quarantine social-engineering, allow benign, strip covert."""

    def __init__(self, *, tools: list[str] | None = None) -> None:
        self.tools = tools if tools is not None else ["send_message", "echo"]

    async def call_tool(self, name: str, args: dict) -> ToolResult:
        payload = str(args.get("input", ""))
        if payload in SOCIAL_ENGINEERING_PAYLOADS or payload == AISI_MAINTAINER_PRESSURE_PAYLOAD:
            return ToolResult(
                content=[Content(text="SEMANTIC_QUARANTINE: social engineering blocked", isError=True)],
                isError=True,
            )
        if payload in BENIGN_EGRESS_CONTROLS:
            return ToolResult(content=[Content(text="sent")])
        if payload in COVERT_CHANNEL_PAYLOADS:
            # Canonicalize: strip zero-width / homoglyph / collapse spaces.
            cleaned = (
                payload.replace("\u200b", "")
                .replace("\u0430", "a")
            )
            cleaned = " ".join(cleaned.split())
            return ToolResult(content=[Content(text=cleaned)])
        return ToolResult(content=[Content(text="ok")])

    async def list_tools(self) -> SimpleNamespace:
        return SimpleNamespace(
            tools=[SimpleNamespace(name=n) for n in self.tools],
        )


class EchoCovertSession:
    async def call_tool(self, name: str, args: dict) -> ToolResult:
        return ToolResult(content=[Content(text=str(args.get("input", "")))])


class AlwaysAllowSession:
    async def call_tool(self, name: str, args: dict) -> ToolResult:
        return ToolResult(content=[Content(text="ok")])


class AlwaysBlockBenignSession:
    async def call_tool(self, name: str, args: dict) -> ToolResult:
        return ToolResult(
            content=[Content(text="denied", isError=True)],
            isError=True,
        )


@pytest.mark.security
@pytest.mark.asyncio
async def test_social_engineering_corpus_quarantined() -> None:
    session = RecordedEgressSession()
    await assert_egress_quarantined(session, "send_message")


@pytest.mark.security
@pytest.mark.asyncio
async def test_benign_egress_controls_allowed() -> None:
    session = RecordedEgressSession()
    await assert_egress_allowed(session, "send_message")


@pytest.mark.security
@pytest.mark.asyncio
async def test_known_covert_encodings_neutralized() -> None:
    session = RecordedEgressSession()
    await assert_covert_channel_neutralized(session, "send_message")


@pytest.mark.security
@pytest.mark.asyncio
async def test_capability_reduction_forbids_general_exec() -> None:
    session = RecordedEgressSession(tools=["send_message", "read_file"])
    await assert_general_exec_tools_absent(session)


@pytest.mark.security
@pytest.mark.asyncio
async def test_capability_reduction_fails_when_shell_exposed() -> None:
    session = RecordedEgressSession(tools=["send_message", "shell"])
    with pytest.raises(MCPAssertionError, match="Capability reduction"):
        await assert_general_exec_tools_absent(session)


@pytest.mark.security
@pytest.mark.asyncio
async def test_egress_quarantine_fails_without_deny() -> None:
    with pytest.raises(MCPAssertionError, match="did not quarantine"):
        await assert_egress_quarantined(AlwaysAllowSession(), "send_message")


@pytest.mark.security
@pytest.mark.asyncio
async def test_egress_allowed_fails_on_false_positive() -> None:
    with pytest.raises(MCPAssertionError, match="falsely blocked"):
        await assert_egress_allowed(AlwaysBlockBenignSession(), "send_message")


@pytest.mark.security
@pytest.mark.asyncio
async def test_covert_fails_when_markers_echoed() -> None:
    with pytest.raises(MCPAssertionError, match="did not neutralize"):
        await assert_covert_channel_neutralized(EchoCovertSession(), "send_message")


@pytest.mark.security
@pytest.mark.skip(
    reason=(
        "AISI maintainer-pressure / synthetic-identity egress guard not landed yet "
        "(known-gap issue #48 — convert to enforced test when bastion Extension A ships)."
    ),
)
@pytest.mark.asyncio
async def test_aisi_regression_maintainer_pressure_quarantined() -> None:
    """Visible skip until bastion semantic egress guard lands — not a silent xfail."""
    session = RecordedEgressSession()
    await assert_egress_quarantined(
        session,
        "send_message",
        payloads=(AISI_MAINTAINER_PRESSURE_PAYLOAD,),
    )


@pytest.mark.asyncio
async def test_list_tools_dict_shape_and_custom_forbidden() -> None:
    class DictListSession:
        async def list_tools(self) -> dict:
            return {"tools": [{"name": "echo"}, {"name": "run_command"}]}

    with pytest.raises(MCPAssertionError, match="run_command"):
        await assert_general_exec_tools_absent(
            DictListSession(),
            forbidden_names=("run_command",),
        )


@pytest.mark.asyncio
async def test_egress_quarantine_skips_raised_and_flags_missing_substring() -> None:
    class Mixed:
        def __init__(self) -> None:
            self.n = 0

        async def call_tool(self, name: str, args: dict) -> ToolResult:
            self.n += 1
            if self.n == 1:
                raise RuntimeError("transport")
            return ToolResult(
                content=[Content(text="denied for policy", isError=True)],
                isError=True,
            )

    with pytest.raises(MCPAssertionError, match="error missing"):
        await assert_egress_quarantined(
            Mixed(),
            "send_message",
            payloads=("a", "b"),
        )


@pytest.mark.asyncio
async def test_egress_allowed_records_raised_exception() -> None:
    class Boom:
        async def call_tool(self, name: str, args: dict) -> ToolResult:
            raise ConnectionError("down")

    with pytest.raises(MCPAssertionError, match="raised ConnectionError"):
        await assert_egress_allowed(Boom(), "send_message", payloads=("ok note",))


@pytest.mark.asyncio
async def test_covert_skips_raise_and_error_responses() -> None:
    class MixCovert:
        def __init__(self) -> None:
            self.n = 0

        async def call_tool(self, name: str, args: dict) -> ToolResult:
            self.n += 1
            if self.n == 1:
                raise RuntimeError("x")
            return ToolResult(
                content=[Content(text="blocked", isError=True)],
                isError=True,
            )

    await assert_covert_channel_neutralized(
        MixCovert(),
        "send_message",
        payloads=("approve\u200bthis", "аpprove"),
    )
