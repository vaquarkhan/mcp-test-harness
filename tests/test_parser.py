"""Tests for mcp_test_harness.parser."""

from __future__ import annotations

import json

import pytest

from mcp_test_harness.models import JsonRpcError, ParsedMessage
from mcp_test_harness.parser import (
    ParseError,
    parse_message,
    pretty_print,
    serialize_message,
)


# ---------------------------------------------------------------------------
# parse_message
# ---------------------------------------------------------------------------


class TestParseMessage:
    """Tests for parse_message()."""

    def test_parse_request(self) -> None:
        raw = json.dumps(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "echo"}}
        ).encode()
        msg = parse_message(raw)
        assert msg.id == 1
        assert msg.method == "tools/call"
        assert msg.params == {"name": "echo"}
        assert msg.result is None
        assert msg.error is None
        assert msg.raw == raw

    def test_parse_response(self) -> None:
        raw = json.dumps({"jsonrpc": "2.0", "id": 2, "result": {"content": "hello"}}).encode()
        msg = parse_message(raw)
        assert msg.id == 2
        assert msg.method is None
        assert msg.result == {"content": "hello"}

    def test_parse_notification(self) -> None:
        raw = json.dumps({"jsonrpc": "2.0", "method": "notifications/progress"}).encode()
        msg = parse_message(raw)
        assert msg.id is None
        assert msg.method == "notifications/progress"

    def test_parse_error_response(self) -> None:
        raw = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "error": {"code": -32600, "message": "Invalid Request", "data": "extra"},
            }
        ).encode()
        msg = parse_message(raw)
        assert msg.error is not None
        assert msg.error.code == -32600
        assert msg.error.message == "Invalid Request"
        assert msg.error.data == "extra"

    def test_parse_error_without_data(self) -> None:
        raw = json.dumps(
            {"jsonrpc": "2.0", "id": 4, "error": {"code": -32601, "message": "Not found"}}
        ).encode()
        msg = parse_message(raw)
        assert msg.error is not None
        assert msg.error.data is None

    def test_parse_invalid_json_raises(self) -> None:
        raw = b"not json at all"
        with pytest.raises(ParseError) as exc_info:
            parse_message(raw)
        assert exc_info.value.raw == raw

    def test_parse_non_object_raises(self) -> None:
        raw = b"[1, 2, 3]"
        with pytest.raises(ParseError) as exc_info:
            parse_message(raw)
        assert exc_info.value.raw == raw

    def test_parse_string_id(self) -> None:
        raw = json.dumps({"jsonrpc": "2.0", "id": "abc-123", "result": True}).encode()
        msg = parse_message(raw)
        assert msg.id == "abc-123"


# ---------------------------------------------------------------------------
# serialize_message
# ---------------------------------------------------------------------------


class TestSerializeMessage:
    """Tests for serialize_message()."""

    def test_serialize_request(self) -> None:
        msg = ParsedMessage(
            id=1, method="tools/list", params=None, result=None, error=None, raw=b""
        )
        data = json.loads(serialize_message(msg))
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == 1
        assert data["method"] == "tools/list"
        assert "params" not in data
        assert "result" not in data

    def test_serialize_error_response(self) -> None:
        msg = ParsedMessage(
            id=5,
            method=None,
            params=None,
            result=None,
            error=JsonRpcError(code=-32600, message="bad", data=None),
            raw=b"",
        )
        data = json.loads(serialize_message(msg))
        assert data["error"]["code"] == -32600
        assert "data" not in data["error"]

    def test_serialize_error_with_data(self) -> None:
        msg = ParsedMessage(
            id=6,
            method=None,
            params=None,
            result=None,
            error=JsonRpcError(code=-1, message="err", data={"detail": "x"}),
            raw=b"",
        )
        data = json.loads(serialize_message(msg))
        assert data["error"]["data"] == {"detail": "x"}


# ---------------------------------------------------------------------------
# Round-trip property
# ---------------------------------------------------------------------------


class TestRoundTrip:
    """parse -> serialize -> parse produces equivalent ParsedMessage."""

    @staticmethod
    def _messages_equivalent(a: ParsedMessage, b: ParsedMessage) -> bool:
        """Compare two ParsedMessages ignoring raw bytes."""
        return (
            a.id == b.id
            and a.method == b.method
            and a.params == b.params
            and a.result == b.result
            and _errors_equal(a.error, b.error)
        )

    def test_round_trip_request(self) -> None:
        raw = json.dumps(
            {"jsonrpc": "2.0", "id": 10, "method": "tools/call", "params": {"x": 1}}
        ).encode()
        first = parse_message(raw)
        second = parse_message(serialize_message(first))
        assert self._messages_equivalent(first, second)

    def test_round_trip_response(self) -> None:
        raw = json.dumps({"jsonrpc": "2.0", "id": 11, "result": [1, 2, 3]}).encode()
        first = parse_message(raw)
        second = parse_message(serialize_message(first))
        assert self._messages_equivalent(first, second)

    def test_round_trip_error(self) -> None:
        raw = json.dumps(
            {"jsonrpc": "2.0", "id": 12, "error": {"code": -1, "message": "oops", "data": None}}
        ).encode()
        first = parse_message(raw)
        second = parse_message(serialize_message(first))
        assert self._messages_equivalent(first, second)

    def test_round_trip_notification(self) -> None:
        raw = json.dumps({"jsonrpc": "2.0", "method": "log"}).encode()
        first = parse_message(raw)
        second = parse_message(serialize_message(first))
        assert self._messages_equivalent(first, second)


# ---------------------------------------------------------------------------
# pretty_print
# ---------------------------------------------------------------------------


class TestPrettyPrint:
    """Tests for pretty_print()."""

    def test_plain_output_contains_method(self) -> None:
        msg = parse_message(
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}).encode()
        )
        output = pretty_print(msg, syntax_highlight=False)
        assert "Request" in output
        assert '"tools/list"' in output

    def test_notification_label(self) -> None:
        msg = parse_message(
            json.dumps({"jsonrpc": "2.0", "method": "notifications/progress"}).encode()
        )
        output = pretty_print(msg, syntax_highlight=False)
        assert "Notification" in output

    def test_error_response_label(self) -> None:
        msg = parse_message(
            json.dumps(
                {"jsonrpc": "2.0", "id": 1, "error": {"code": -1, "message": "fail"}}
            ).encode()
        )
        output = pretty_print(msg, syntax_highlight=False)
        assert "Error Response" in output

    def test_response_label(self) -> None:
        msg = parse_message(
            json.dumps({"jsonrpc": "2.0", "id": 1, "result": "ok"}).encode()
        )
        output = pretty_print(msg, syntax_highlight=False)
        assert "Response" in output

    def test_syntax_highlight_contains_ansi(self) -> None:
        msg = parse_message(
            json.dumps({"jsonrpc": "2.0", "id": 1, "result": "ok"}).encode()
        )
        output = pretty_print(msg, syntax_highlight=True)
        assert "\033[" in output

    def test_redaction_api_key(self) -> None:
        msg = parse_message(
            json.dumps(
                {"jsonrpc": "2.0", "id": 1, "result": {"key": "sk-abc123XYZ"}}
            ).encode()
        )
        output = pretty_print(
            msg,
            redact_patterns=[r"sk-[a-zA-Z0-9]+"],
            syntax_highlight=False,
        )
        assert "sk-abc123XYZ" not in output
        assert "[REDACTED]" in output

    def test_redaction_bearer_token(self) -> None:
        msg = parse_message(
            json.dumps(
                {"jsonrpc": "2.0", "id": 1, "result": {"auth": "Bearer eyJhbGciOi.xyz"}}
            ).encode()
        )
        output = pretty_print(
            msg,
            redact_patterns=[r"Bearer [a-zA-Z0-9._-]+"],
            syntax_highlight=False,
        )
        assert "eyJhbGciOi" not in output
        assert "[REDACTED]" in output


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _errors_equal(a: JsonRpcError | None, b: JsonRpcError | None) -> bool:
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return a.code == b.code and a.message == b.message and a.data == b.data
