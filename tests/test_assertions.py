"""Tests for mcp_test_harness.assertions."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

import mcp_test_harness.assertions as assertions_mod
from mcp_test_harness.assertions import (
    MCPAssertionError,
    assert_authorization_boundary,
    assert_capabilities,
    assert_latency,
    assert_prompt,
    assert_resource_read,
    assert_snapshot,
    assert_tool_call,
    assert_tool_denied,
)


# ---------------------------------------------------------------------------
# Fake MCP SDK objects (duck-typed)
# ---------------------------------------------------------------------------


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
    role: str = "assistant"
    content: str = ""


@dataclass
class FakePromptResult:
    messages: list[FakeMessage] = field(default_factory=list)


class FakeSession:
    """Minimal duck-typed session for testing assertion helpers."""

    def __init__(
        self,
        tool_result: FakeToolResult | None = None,
        resource_result: FakeResourceResult | None = None,
        prompt_result: FakePromptResult | None = None,
        capabilities: dict[str, Any] | None = None,
    ) -> None:
        self._tool_result = tool_result or FakeToolResult()
        self._resource_result = resource_result or FakeResourceResult()
        self._prompt_result = prompt_result or FakePromptResult()
        self.server_capabilities = capabilities

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> FakeToolResult:
        return self._tool_result

    async def read_resource(self, uri: str) -> FakeResourceResult:
        return self._resource_result

    async def get_prompt(
        self, name: str, arguments: dict[str, str] | None = None
    ) -> FakePromptResult:
        return self._prompt_result


# ---------------------------------------------------------------------------
# assert_tool_call
# ---------------------------------------------------------------------------


class TestAssertToolCall:
    def test_pass_no_expected(self) -> None:
        session = FakeSession(
            tool_result=FakeToolResult(content=[FakeContent(text="ok")])
        )
        result = asyncio.run(
            assert_tool_call(session, "my_tool", {"a": 1})
        )
        assert result.content[0].text == "ok"

    def test_pass_with_expected(self) -> None:
        session = FakeSession(
            tool_result=FakeToolResult(content=[FakeContent(text="hello")])
        )
        expected = [{"text": "hello", "isError": False}]
        asyncio.run(
            assert_tool_call(session, "t", {}, expected=expected)
        )

    def test_fail_mismatch(self) -> None:
        session = FakeSession(
            tool_result=FakeToolResult(content=[FakeContent(text="actual")])
        )
        expected = [{"text": "expected", "isError": False}]
        with pytest.raises(MCPAssertionError, match="response mismatch"):
            asyncio.run(
                assert_tool_call(session, "t", {}, expected=expected)
            )

    def test_fail_server_error(self) -> None:
        session = FakeSession(
            tool_result=FakeToolResult(
                content=[FakeContent(text="boom", isError=True)]
            )
        )
        with pytest.raises(MCPAssertionError, match="returned an error.*boom"):
            asyncio.run(
                assert_tool_call(session, "t", {})
            )

    def test_diff_in_error(self) -> None:
        session = FakeSession(
            tool_result=FakeToolResult(content=[FakeContent(text="a")])
        )
        with pytest.raises(MCPAssertionError) as exc_info:
            asyncio.run(
                assert_tool_call(session, "t", {}, expected=[{"text": "b", "isError": False}])
            )
        assert exc_info.value.diff is not None
        assert "expected" in exc_info.value.diff
        assert "actual" in exc_info.value.diff


# ---------------------------------------------------------------------------
# assert_resource_read
# ---------------------------------------------------------------------------


class TestAssertResourceRead:
    def test_pass_content(self) -> None:
        session = FakeSession(
            resource_result=FakeResourceResult(
                contents=[FakeResourceContent(text="data", mimeType="text/plain")]
            )
        )
        asyncio.run(
            assert_resource_read(session, "file:///a.txt", expected_content="data")
        )

    def test_pass_mime(self) -> None:
        session = FakeSession(
            resource_result=FakeResourceResult(
                contents=[FakeResourceContent(text="x", mimeType="application/json")]
            )
        )
        asyncio.run(
            assert_resource_read(
                session, "file:///a", expected_mime_type="application/json"
            )
        )

    def test_fail_content_mismatch(self) -> None:
        session = FakeSession(
            resource_result=FakeResourceResult(
                contents=[FakeResourceContent(text="actual")]
            )
        )
        with pytest.raises(MCPAssertionError, match="content mismatch"):
            asyncio.run(
                assert_resource_read(session, "u", expected_content="expected")
            )

    def test_fail_mime_mismatch(self) -> None:
        session = FakeSession(
            resource_result=FakeResourceResult(
                contents=[FakeResourceContent(mimeType="text/html")]
            )
        )
        with pytest.raises(MCPAssertionError, match="MIME type mismatch"):
            asyncio.run(
                assert_resource_read(session, "u", expected_mime_type="text/plain")
            )

    def test_fail_no_contents(self) -> None:
        session = FakeSession(
            resource_result=FakeResourceResult(contents=[])
        )
        with pytest.raises(MCPAssertionError, match="no content items"):
            asyncio.run(
                assert_resource_read(session, "u")
            )


# ---------------------------------------------------------------------------
# assert_prompt
# ---------------------------------------------------------------------------


class TestAssertPrompt:
    def test_pass(self) -> None:
        session = FakeSession(
            prompt_result=FakePromptResult(
                messages=[FakeMessage(role="assistant", content="hi")]
            )
        )
        expected = [{"role": "assistant", "content": "hi"}]
        asyncio.run(
            assert_prompt(session, "greet", expected_messages=expected)
        )

    def test_fail_mismatch(self) -> None:
        session = FakeSession(
            prompt_result=FakePromptResult(
                messages=[FakeMessage(role="user", content="x")]
            )
        )
        expected = [{"role": "assistant", "content": "y"}]
        with pytest.raises(MCPAssertionError, match="message structure mismatch"):
            asyncio.run(
                assert_prompt(session, "p", expected_messages=expected)
            )

    def test_no_expected_passes(self) -> None:
        session = FakeSession(
            prompt_result=FakePromptResult(messages=[FakeMessage()])
        )
        asyncio.run(
            assert_prompt(session, "p")
        )


# ---------------------------------------------------------------------------
# assert_capabilities
# ---------------------------------------------------------------------------


class TestAssertCapabilities:
    def test_pass(self) -> None:
        session = FakeSession(capabilities={"tools": True, "prompts": True})
        asyncio.run(
            assert_capabilities(session, {"tools": True})
        )

    def test_fail_missing_key(self) -> None:
        session = FakeSession(capabilities={"tools": True})
        with pytest.raises(MCPAssertionError, match="capabilities mismatch"):
            asyncio.run(
                assert_capabilities(session, {"resources": True})
            )

    def test_fail_value_mismatch(self) -> None:
        session = FakeSession(capabilities={"tools": False})
        with pytest.raises(MCPAssertionError, match="capabilities mismatch"):
            asyncio.run(
                assert_capabilities(session, {"tools": True})
            )

    def test_fail_no_capabilities(self) -> None:
        session = FakeSession()
        with pytest.raises(MCPAssertionError, match="no.*capabilities"):
            asyncio.run(
                assert_capabilities(session, {"tools": True})
            )

    def test_diff_in_error(self) -> None:
        session = FakeSession(capabilities={"tools": False})
        with pytest.raises(MCPAssertionError) as exc_info:
            asyncio.run(
                assert_capabilities(session, {"tools": True})
            )
        assert exc_info.value.diff is not None


# ---------------------------------------------------------------------------
# assert_snapshot
# ---------------------------------------------------------------------------


class TestAssertSnapshot:
    def test_creates_snapshot_when_missing(self, tmp_path: Path) -> None:
        test_file = tmp_path / "test_example.py"
        test_file.touch()
        asyncio.run(
            assert_snapshot({"key": "value"}, "my_snap", test_file)
        )
        snap = tmp_path / "__snapshots__" / "my_snap.snap"
        assert snap.exists()
        data = json.loads(snap.read_text())
        assert data == {"key": "value"}

    def test_passes_when_matches(self, tmp_path: Path) -> None:
        test_file = tmp_path / "test_example.py"
        test_file.touch()
        snap_dir = tmp_path / "__snapshots__"
        snap_dir.mkdir()
        snap = snap_dir / "s.snap"
        snap.write_text(json.dumps({"a": 1}, indent=2, sort_keys=True) + "\n")
        asyncio.run(
            assert_snapshot({"a": 1}, "s", test_file)
        )

    def test_fails_on_mismatch(self, tmp_path: Path) -> None:
        test_file = tmp_path / "test_example.py"
        test_file.touch()
        snap_dir = tmp_path / "__snapshots__"
        snap_dir.mkdir()
        snap = snap_dir / "s.snap"
        snap.write_text(json.dumps({"a": 1}, indent=2, sort_keys=True) + "\n")
        with pytest.raises(MCPAssertionError, match="Snapshot mismatch"):
            asyncio.run(
                assert_snapshot({"a": 2}, "s", test_file)
            )

    def test_update_overwrites(self, tmp_path: Path) -> None:
        test_file = tmp_path / "test_example.py"
        test_file.touch()
        snap_dir = tmp_path / "__snapshots__"
        snap_dir.mkdir()
        snap = snap_dir / "s.snap"
        snap.write_text(json.dumps({"old": True}, indent=2, sort_keys=True) + "\n")
        asyncio.run(
            assert_snapshot({"new": True}, "s", test_file, update=True)
        )
        data = json.loads(snap.read_text())
        assert data == {"new": True}


# ---------------------------------------------------------------------------
# Extended FakeSession for list operations
# ---------------------------------------------------------------------------


@dataclass
class FakeTool:
    name: str = ""


@dataclass
class FakeToolListResult:
    tools: list[FakeTool] = field(default_factory=list)


@dataclass
class FakeResource:
    uri: str = ""


@dataclass
class FakeResourceListResult:
    resources: list[FakeResource] = field(default_factory=list)


class FakeSessionExtended(FakeSession):
    """Extended fake session with list_tools / list_resources support."""

    def __init__(
        self,
        tool_result: FakeToolResult | None = None,
        resource_result: FakeResourceResult | None = None,
        prompt_result: FakePromptResult | None = None,
        capabilities: dict[str, Any] | None = None,
        tool_list_result: FakeToolListResult | None = None,
        resource_list_result: FakeResourceListResult | None = None,
        call_tool_error: Exception | None = None,
    ) -> None:
        super().__init__(tool_result, resource_result, prompt_result, capabilities)
        self._tool_list_result = tool_list_result or FakeToolListResult()
        self._resource_list_result = resource_list_result or FakeResourceListResult()
        self._call_tool_error = call_tool_error

    async def list_tools(self) -> FakeToolListResult:
        return self._tool_list_result

    async def list_resources(self) -> FakeResourceListResult:
        return self._resource_list_result

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> FakeToolResult:
        if arguments.get("role") == "admin":
            return FakeToolResult(content=[FakeContent(text="ok", isError=False)])
        if arguments.get("role") == "guest":
            return FakeToolResult(content=[FakeContent(text="forbidden", isError=True)])
        if self._call_tool_error is not None:
            raise self._call_tool_error
        return self._tool_result


from mcp_test_harness.assertions import (
    assert_tool_list,
    assert_resource_list,
    assert_tool_rejects,
    assert_invalid_tool,
)


# ---------------------------------------------------------------------------
# assert_tool_list
# ---------------------------------------------------------------------------


class TestAssertToolList:
    def test_pass_exact_match(self) -> None:
        session = FakeSessionExtended(
            tool_list_result=FakeToolListResult(
                tools=[FakeTool(name="echo"), FakeTool(name="add")]
            )
        )
        asyncio.run(assert_tool_list(session, ["echo", "add"]))

    def test_pass_subset(self) -> None:
        session = FakeSessionExtended(
            tool_list_result=FakeToolListResult(
                tools=[FakeTool(name="echo"), FakeTool(name="add"), FakeTool(name="mul")]
            )
        )
        asyncio.run(assert_tool_list(session, ["echo"]))

    def test_fail_missing_tool(self) -> None:
        session = FakeSessionExtended(
            tool_list_result=FakeToolListResult(
                tools=[FakeTool(name="echo")]
            )
        )
        with pytest.raises(MCPAssertionError, match="Missing tools"):
            asyncio.run(assert_tool_list(session, ["echo", "missing_tool"]))

    def test_pass_empty_expected(self) -> None:
        session = FakeSessionExtended(
            tool_list_result=FakeToolListResult(tools=[FakeTool(name="echo")])
        )
        asyncio.run(assert_tool_list(session, []))


# ---------------------------------------------------------------------------
# assert_resource_list
# ---------------------------------------------------------------------------


class TestAssertResourceList:
    def test_pass_exact_match(self) -> None:
        session = FakeSessionExtended(
            resource_list_result=FakeResourceListResult(
                resources=[FakeResource(uri="file:///a"), FakeResource(uri="file:///b")]
            )
        )
        asyncio.run(assert_resource_list(session, ["file:///a", "file:///b"]))

    def test_pass_subset(self) -> None:
        session = FakeSessionExtended(
            resource_list_result=FakeResourceListResult(
                resources=[FakeResource(uri="file:///a"), FakeResource(uri="file:///b")]
            )
        )
        asyncio.run(assert_resource_list(session, ["file:///a"]))

    def test_fail_missing_uri(self) -> None:
        session = FakeSessionExtended(
            resource_list_result=FakeResourceListResult(
                resources=[FakeResource(uri="file:///a")]
            )
        )
        with pytest.raises(MCPAssertionError, match="Missing resources"):
            asyncio.run(assert_resource_list(session, ["file:///a", "file:///missing"]))

    def test_pass_empty_expected(self) -> None:
        session = FakeSessionExtended(
            resource_list_result=FakeResourceListResult(
                resources=[FakeResource(uri="file:///a")]
            )
        )
        asyncio.run(assert_resource_list(session, []))


# ---------------------------------------------------------------------------
# assert_tool_rejects
# ---------------------------------------------------------------------------


class TestAssertToolRejects:
    def test_pass_when_tool_returns_error(self) -> None:
        session = FakeSessionExtended(
            tool_result=FakeToolResult(
                content=[FakeContent(text="bad input", isError=True)]
            )
        )
        asyncio.run(assert_tool_rejects(session, "bad_tool", {"x": 1}))

    def test_pass_when_tool_raises(self) -> None:
        session = FakeSessionExtended(
            call_tool_error=RuntimeError("connection refused")
        )
        asyncio.run(assert_tool_rejects(session, "bad_tool", {}))

    def test_fail_when_tool_succeeds(self) -> None:
        session = FakeSessionExtended(
            tool_result=FakeToolResult(
                content=[FakeContent(text="ok", isError=False)]
            )
        )
        with pytest.raises(MCPAssertionError, match="Expected tool.*to return an error"):
            asyncio.run(assert_tool_rejects(session, "good_tool", {}))

    def test_error_substring_match(self) -> None:
        session = FakeSessionExtended(
            tool_result=FakeToolResult(
                content=[FakeContent(text="invalid argument: x", isError=True)]
            )
        )
        asyncio.run(
            assert_tool_rejects(session, "t", {"x": 1}, error_substring="invalid argument")
        )

    def test_error_substring_mismatch(self) -> None:
        session = FakeSessionExtended(
            tool_result=FakeToolResult(
                content=[FakeContent(text="some error", isError=True)]
            )
        )
        with pytest.raises(MCPAssertionError, match="does not contain"):
            asyncio.run(
                assert_tool_rejects(session, "t", {}, error_substring="not found")
            )

    def test_raises_with_substring_match(self) -> None:
        session = FakeSessionExtended(
            call_tool_error=RuntimeError("connection refused")
        )
        asyncio.run(
            assert_tool_rejects(session, "t", {}, error_substring="connection")
        )

    def test_raises_with_substring_mismatch(self) -> None:
        session = FakeSessionExtended(
            call_tool_error=RuntimeError("connection refused")
        )
        with pytest.raises(MCPAssertionError, match="does not contain"):
            asyncio.run(
                assert_tool_rejects(session, "t", {}, error_substring="timeout")
            )


# ---------------------------------------------------------------------------
# assert_invalid_tool
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# assert_latency
# ---------------------------------------------------------------------------


class _SleepSession:
    """Session whose call_tool sleeps a fixed time (for perf assertions)."""

    def __init__(self, sleep_ms: float) -> None:
        self._sleep_ms = sleep_ms

    async def call_tool(self, *args: object, **kwargs: object) -> FakeToolResult:
        await asyncio.sleep(self._sleep_ms / 1000.0)
        return FakeToolResult(content=[FakeContent(text="ok")])


class _IndexedSleepSession:
    """Sleep duration chosen by 0-based call index (for warmup + mixed timings)."""

    def __init__(self, per_call_ms: list[float]) -> None:
        self._per = per_call_ms
        self._i = 0

    async def call_tool(self, *args: object, **kwargs: object) -> FakeToolResult:
        ms = self._per[self._i] if self._i < len(self._per) else self._per[-1]
        self._i += 1
        await asyncio.sleep(ms / 1000.0)
        return FakeToolResult(content=[FakeContent(text="ok")])


_agg = assertions_mod._aggregate_latency_ms  # type: ignore[attr-defined]


class TestAggregateLatencyMs:
    def test_empty(self) -> None:
        assert _agg([], "p95") == 0.0

    def test_percentile_single_sample(self) -> None:
        assert _agg([12.0], "p99") == 12.0

    def test_max_mean_median(self) -> None:
        t = [1.0, 2.0, 9.0, 3.0]
        assert _agg(t, "max") == 9.0
        assert _agg(t, "mean") == 3.75
        assert _agg(t, "median") == 2.5

    def test_p95_p99_interpolation(self) -> None:
        p = [0.0, 10.0]
        v = _agg(p, "p95")
        assert 9.0 < v < 10.0

    def test_percentile_hits_exact_rank_index(self) -> None:
        s = [float(i) for i in range(21)]
        assert _agg(s, "p95") == s[19]

    def test_p99(self) -> None:
        t = [1.0, 2.0, 3.0, 4.0, 5.0]
        assert 4.0 < _agg(t, "p99") <= 5.0


class TestAssertLatency:
    def test_pass_single_run(self) -> None:
        s = _SleepSession(0.0)
        asyncio.run(
            assert_latency(s, "t", {}, max_ms=5000.0),
        )

    def test_fail_too_slow(self) -> None:
        s = _SleepSession(50.0)
        with pytest.raises(MCPAssertionError, match="exceeds budget"):
            asyncio.run(
                assert_latency(s, "t", {}, max_ms=1.0),
            )

    def test_p95_agg_fails(self) -> None:
        s = _SleepSession(20.0)
        with pytest.raises(MCPAssertionError, match="exceeds budget"):
            asyncio.run(
                assert_latency(
                    s, "t", {}, max_ms=1.0, runs=4, aggregate="p95"
                )
            )

    def test_p95_agg_passes(self) -> None:
        s = _SleepSession(0.0)
        asyncio.run(
            assert_latency(
                s, "t", {}, max_ms=100.0, runs=3, aggregate="p95"
            )
        )

    def test_warmup_not_in_timings_for_budget(self) -> None:
        s = _IndexedSleepSession([200.0, 200.0, 0.0])
        asyncio.run(
            assert_latency(
                s, "t", {}, max_ms=10.0, warmup=2, runs=1, aggregate="max"
            )
        )


class TestAssertInvalidTool:
    def test_pass_when_tool_errors(self) -> None:
        session = FakeSessionExtended(
            tool_result=FakeToolResult(
                content=[FakeContent(text="unknown tool", isError=True)]
            )
        )
        asyncio.run(assert_invalid_tool(session, "nonexistent_tool"))

    def test_fail_when_tool_succeeds(self) -> None:
        session = FakeSessionExtended(
            tool_result=FakeToolResult(
                content=[FakeContent(text="ok", isError=False)]
            )
        )
        with pytest.raises(MCPAssertionError, match="Expected tool.*to return an error"):
            asyncio.run(assert_invalid_tool(session, "actually_exists"))


class TestAuthorizationAssertions:
    def test_assert_tool_denied_passes(self) -> None:
        session = FakeSessionExtended()
        asyncio.run(
            assert_tool_denied(
                session,
                "write_funds",
                {"role": "guest", "amount": 10},
                error_substring="forbidden",
            )
        )

    def test_assert_tool_denied_fails_when_allowed(self) -> None:
        session = FakeSessionExtended()
        with pytest.raises(MCPAssertionError, match="Expected tool.*to return an error"):
            asyncio.run(
                assert_tool_denied(
                    session,
                    "write_funds",
                    {"role": "admin", "amount": 10},
                )
            )

    def test_assert_authorization_boundary_passes(self) -> None:
        session = FakeSessionExtended()
        asyncio.run(
            assert_authorization_boundary(
                session,
                "write_funds",
                allowed_arguments={"role": "admin", "amount": 10},
                denied_arguments={"role": "guest", "amount": 10},
                denied_error_substring="forbidden",
            )
        )

    def test_assert_authorization_boundary_fails_when_denied_is_allowed(self) -> None:
        session = FakeSessionExtended()
        with pytest.raises(MCPAssertionError, match="Expected tool.*to return an error"):
            asyncio.run(
                assert_authorization_boundary(
                    session,
                    "write_funds",
                    allowed_arguments={"role": "admin", "amount": 10},
                    denied_arguments={"role": "admin", "amount": 10},
                )
            )
