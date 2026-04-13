"""MCP JSON-RPC message parser, serializer, and pretty printer.

Provides:
- ``parse_message``  -- parse raw bytes into a typed ``ParsedMessage``
- ``serialize_message`` -- serialize a ``ParsedMessage`` back to JSON-RPC bytes
- ``pretty_print`` -- human-readable, syntax-highlighted, optionally redacted output
- ``ParseError`` -- raised when raw bytes cannot be decoded as valid JSON-RPC
"""

from __future__ import annotations

import json
import re
from typing import Any

from mcp_test_harness.models import JsonRpcError, ParsedMessage

__all__ = [
    "ParseError",
    "parse_message",
    "pretty_print",
    "serialize_message",
]


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ParseError(Exception):
    """Raised when raw bytes cannot be parsed as a JSON-RPC message.

    Attributes:
        raw: The original bytes that failed to parse.
    """

    def __init__(self, message: str, raw: bytes) -> None:
        super().__init__(message)
        self.raw = raw


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def parse_message(raw: bytes) -> ParsedMessage:
    """Parse raw bytes into a typed :class:`ParsedMessage`.

    Supports JSON-RPC 2.0 requests, responses, notifications, and error
    responses.  The ``raw`` field of the returned object always stores the
    original bytes.

    Raises:
        ParseError: If *raw* is not valid JSON or does not look like a
            JSON-RPC message (i.e. not a JSON object).
    """
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ParseError(f"Invalid JSON: {exc}", raw) from exc

    if not isinstance(data, dict):
        raise ParseError(
            f"Expected a JSON object, got {type(data).__name__}", raw
        )

    error_obj: JsonRpcError | None = None
    raw_error = data.get("error")
    if isinstance(raw_error, dict):
        error_obj = JsonRpcError(
            code=raw_error.get("code", 0),
            message=raw_error.get("message", ""),
            data=raw_error.get("data"),
        )

    return ParsedMessage(
        id=data.get("id"),
        method=data.get("method"),
        params=data.get("params"),
        result=data.get("result"),
        error=error_obj,
        raw=raw,
    )


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


def serialize_message(message: ParsedMessage) -> bytes:
    """Serialize a :class:`ParsedMessage` back to JSON-RPC bytes.

    Only fields that are semantically present are included so that the
    round-trip property holds:

        ``parse_message(serialize_message(parse_message(raw)))``

    produces an equivalent ``ParsedMessage``.
    """
    obj: dict[str, Any] = {"jsonrpc": "2.0"}

    if message.id is not None:
        obj["id"] = message.id

    if message.method is not None:
        obj["method"] = message.method

    if message.params is not None:
        obj["params"] = message.params

    if message.result is not None:
        obj["result"] = message.result

    if message.error is not None:
        err: dict[str, Any] = {
            "code": message.error.code,
            "message": message.error.message,
        }
        if message.error.data is not None:
            err["data"] = message.error.data
        obj["error"] = err

    return json.dumps(obj, separators=(",", ":")).encode("utf-8")


# ---------------------------------------------------------------------------
# Pretty printing helpers (ANSI escape codes, no external deps)
# ---------------------------------------------------------------------------

# ANSI colour codes
_RESET = "\033[0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_CYAN = "\033[36m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_RED = "\033[31m"
_MAGENTA = "\033[35m"


def _colorize_json(text: str) -> str:
    """Apply ANSI syntax highlighting to a JSON string."""

    def _replacer(match: re.Match[str]) -> str:
        token = match.group(0)
        if token.startswith('"'):
            # Distinguish keys (followed by ':') from string values
            if match.end() < len(text) and text[match.end() :].lstrip().startswith(":"):
                return f"{_CYAN}{token}{_RESET}"
            return f"{_GREEN}{token}{_RESET}"
        if token in ("true", "false"):
            return f"{_YELLOW}{token}{_RESET}"
        if token == "null":
            return f"{_MAGENTA}{token}{_RESET}"
        # numbers
        return f"{_YELLOW}{token}{_RESET}"

    # Match JSON tokens: strings, numbers, booleans, null
    pattern = r'"(?:[^"\\]|\\.)*"|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?|\btrue\b|\bfalse\b|\bnull\b'
    return re.sub(pattern, _replacer, text)


def _redact_values(text: str, patterns: list[str]) -> str:
    """Replace values matching any of *patterns* with ``[REDACTED]``."""
    for pat in patterns:
        text = re.sub(pat, "[REDACTED]", text)
    return text


# ---------------------------------------------------------------------------
# Public pretty_print
# ---------------------------------------------------------------------------


def pretty_print(
    message: ParsedMessage,
    redact_patterns: list[str] | None = None,
    syntax_highlight: bool = True,
) -> str:
    """Format a parsed message as human-readable text.

    Parameters:
        message: The parsed JSON-RPC message.
        redact_patterns: Optional list of regex patterns.  Any value in the
            formatted output matching a pattern is replaced with
            ``[REDACTED]``.
        syntax_highlight: When *True* (default), ANSI escape codes are used
            for syntax highlighting.
    """
    # Reconstruct a dict from the ParsedMessage for display
    obj: dict[str, Any] = {"jsonrpc": "2.0"}

    if message.id is not None:
        obj["id"] = message.id
    if message.method is not None:
        obj["method"] = message.method
    if message.params is not None:
        obj["params"] = message.params
    if message.result is not None:
        obj["result"] = message.result
    if message.error is not None:
        err: dict[str, Any] = {
            "code": message.error.code,
            "message": message.error.message,
        }
        if message.error.data is not None:
            err["data"] = message.error.data
        obj["error"] = err

    # Build a header line describing the message type
    if message.method and message.id is not None:
        kind = f"{_BOLD}Request{_RESET}" if syntax_highlight else "Request"
    elif message.method:
        kind = f"{_BOLD}Notification{_RESET}" if syntax_highlight else "Notification"
    elif message.error is not None:
        kind = f"{_RED}{_BOLD}Error Response{_RESET}" if syntax_highlight else "Error Response"
    else:
        kind = f"{_BOLD}Response{_RESET}" if syntax_highlight else "Response"

    header = f"-- {kind} --"

    formatted_json = json.dumps(obj, indent=2)

    # Apply redaction before highlighting so patterns match plain text
    if redact_patterns:
        formatted_json = _redact_values(formatted_json, redact_patterns)

    if syntax_highlight:
        formatted_json = _colorize_json(formatted_json)

    return f"{header}\n{formatted_json}"
