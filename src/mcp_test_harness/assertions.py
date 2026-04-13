"""MCP-specific assertion helpers.

Each helper performs an MCP protocol operation via a client session and
validates the result.  On failure an :class:`MCPAssertionError` is raised
with a diff-style message showing expected vs actual values.
"""

from __future__ import annotations

import difflib
import json
from pathlib import Path
from typing import Any

from mcp_test_harness.snapshots import SnapshotManager


# ---------------------------------------------------------------------------
# Custom error
# ---------------------------------------------------------------------------


class MCPAssertionError(AssertionError):
    """Assertion error that carries diff output for MCP protocol checks."""

    def __init__(self, message: str, diff: str | None = None) -> None:
        self.diff = diff
        full = f"{message}\n{diff}" if diff else message
        super().__init__(full)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _diff_values(expected: Any, actual: Any) -> str:
    """Return a unified-diff string comparing two values as pretty JSON."""
    expected_lines = json.dumps(
        expected, indent=2, sort_keys=True, default=str,
    ).splitlines()
    actual_lines = json.dumps(
        actual, indent=2, sort_keys=True, default=str,
    ).splitlines()
    return "\n".join(
        difflib.unified_diff(
            expected_lines,
            actual_lines,
            fromfile="expected",
            tofile="actual",
            lineterm="",
        )
    )


def _serialize(value: Any) -> Any:
    """Best-effort conversion of an arbitrary object to a JSON-friendly form."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [_serialize(v) for v in value]
    if isinstance(value, dict):
        return {k: _serialize(v) for k, v in value.items()}
    # Duck-type: try common attribute patterns from MCP SDK objects
    if hasattr(value, "__dict__"):
        return {k: _serialize(v) for k, v in value.__dict__.items() if not k.startswith("_")}
    return str(value)


# ---------------------------------------------------------------------------
# assert_tool_call  (Requirement 3.1, 3.4, 3.6)
# ---------------------------------------------------------------------------


async def assert_tool_call(
    session: Any,
    tool_name: str,
    arguments: dict[str, Any],
    expected: Any | None = None,
) -> Any:
    """Invoke a tool on the server and validate the response.

    Parameters
    ----------
    session:
        An MCP ``ClientSession`` (or any duck-typed object with
        ``call_tool(name, arguments)``).
    tool_name:
        Name of the tool to invoke.
    arguments:
        Arguments dict passed to the tool.
    expected:
        If provided, the response content is compared against this value.

    Returns
    -------
    The raw result object from ``session.call_tool``.

    Raises
    ------
    MCPAssertionError
        When the tool returns an error or the response does not match
        *expected*.
    """
    result = await session.call_tool(tool_name, arguments)

    # The MCP SDK result has a `.content` list.  If any content item
    # carries ``isError`` we surface the server error.
    content_items = getattr(result, "content", None) or []
    for item in content_items:
        is_error = getattr(item, "isError", False) or (
            isinstance(item, dict) and item.get("isError", False)
        )
        if is_error:
            text = getattr(item, "text", None) or (
                item.get("text") if isinstance(item, dict) else str(item)
            )
            raise MCPAssertionError(
                f"Tool '{tool_name}' returned an error: {text}",
            )

    if expected is not None:
        actual = _serialize(content_items)
        expected_ser = _serialize(expected)
        if actual != expected_ser:
            diff = _diff_values(expected_ser, actual)
            raise MCPAssertionError(
                f"Tool '{tool_name}' response mismatch",
                diff=diff,
            )

    return result


# ---------------------------------------------------------------------------
# assert_resource_read  (Requirement 3.2, 3.6)
# ---------------------------------------------------------------------------


async def assert_resource_read(
    session: Any,
    resource_uri: str,
    expected_content: str | None = None,
    expected_mime_type: str | None = None,
) -> Any:
    """Read a resource and validate content and MIME type.

    Parameters
    ----------
    session:
        An MCP ``ClientSession`` (or duck-typed equivalent with
        ``read_resource(uri)``).
    resource_uri:
        URI of the resource to read.
    expected_content:
        If provided, the first content item's text is compared.
    expected_mime_type:
        If provided, the first content item's MIME type is compared.

    Returns
    -------
    The raw result object from ``session.read_resource``.

    Raises
    ------
    MCPAssertionError
        When content or MIME type does not match expectations.
    """
    result = await session.read_resource(resource_uri)

    contents = getattr(result, "contents", None) or []
    if not contents:
        raise MCPAssertionError(
            f"Resource '{resource_uri}' returned no content items",
        )

    first = contents[0]
    actual_text = getattr(first, "text", None)
    if actual_text is None and isinstance(first, dict):
        actual_text = first.get("text")

    actual_mime = getattr(first, "mimeType", None)
    if actual_mime is None and isinstance(first, dict):
        actual_mime = first.get("mimeType")

    if expected_content is not None and actual_text != expected_content:
        diff = _diff_values(expected_content, actual_text)
        raise MCPAssertionError(
            f"Resource '{resource_uri}' content mismatch",
            diff=diff,
        )

    if expected_mime_type is not None and actual_mime != expected_mime_type:
        diff = _diff_values(expected_mime_type, actual_mime)
        raise MCPAssertionError(
            f"Resource '{resource_uri}' MIME type mismatch",
            diff=diff,
        )

    return result


# ---------------------------------------------------------------------------
# assert_prompt  (Requirement 3.3, 3.6)
# ---------------------------------------------------------------------------


async def assert_prompt(
    session: Any,
    prompt_name: str,
    arguments: dict[str, str] | None = None,
    expected_messages: list[dict[str, Any]] | None = None,
) -> Any:
    """Get a prompt and validate the message structure.

    Parameters
    ----------
    session:
        An MCP ``ClientSession`` (or duck-typed equivalent with
        ``get_prompt(name, arguments)``).
    prompt_name:
        Name of the prompt to retrieve.
    arguments:
        Optional arguments dict for the prompt.
    expected_messages:
        If provided, the returned messages are compared element-wise.

    Returns
    -------
    The raw result object from ``session.get_prompt``.

    Raises
    ------
    MCPAssertionError
        When the message structure does not match expectations.
    """
    result = await session.get_prompt(prompt_name, arguments)

    messages = getattr(result, "messages", None) or []

    if expected_messages is not None:
        actual_ser = _serialize(messages)
        expected_ser = _serialize(expected_messages)
        if actual_ser != expected_ser:
            diff = _diff_values(expected_ser, actual_ser)
            raise MCPAssertionError(
                f"Prompt '{prompt_name}' message structure mismatch",
                diff=diff,
            )

    return result


# ---------------------------------------------------------------------------
# assert_capabilities  (Requirement 3.5, 3.6)
# ---------------------------------------------------------------------------


async def assert_capabilities(
    session: Any,
    expected: dict[str, Any],
) -> None:
    """Verify the server advertises the expected capabilities.

    The *expected* dict is checked as a **subset** of the actual server
    capabilities -- extra keys on the server side are allowed.

    Parameters
    ----------
    session:
        An MCP ``ClientSession``.  The capabilities are read from
        ``session.server_capabilities`` (set during the initialize
        handshake).  If that attribute is missing the function falls
        back to ``session.capabilities``.
    expected:
        A dict describing the capabilities the server must advertise.

    Raises
    ------
    MCPAssertionError
        When the server capabilities do not contain the expected entries.
    """
    caps = getattr(session, "server_capabilities", None)
    if caps is None:
        caps = getattr(session, "capabilities", None)
    if caps is None:
        raise MCPAssertionError(
            "Session has no 'server_capabilities' or 'capabilities' attribute"
        )

    actual = _serialize(caps)
    if not isinstance(actual, dict):
        actual = {}

    missing: dict[str, Any] = {}
    for key, value in expected.items():
        if key not in actual:
            missing[key] = value
        elif _serialize(value) != _serialize(actual[key]):
            missing[key] = {"expected": value, "actual": actual[key]}

    if missing:
        diff = _diff_values(expected, actual)
        raise MCPAssertionError(
            "Server capabilities mismatch",
            diff=diff,
        )


# ---------------------------------------------------------------------------
# assert_snapshot  (Requirement 15.1, 15.2, 15.3, 15.4)
# ---------------------------------------------------------------------------


async def assert_snapshot(
    actual: Any,
    snapshot_name: str,
    test_file: Path,
    update: bool = False,
) -> None:
    """Compare *actual* against a stored snapshot.

    * Creates the snapshot file when none exists (Req 15.2).
    * In update mode overwrites unconditionally (Req 15.4).
    * On mismatch raises :class:`MCPAssertionError` with a diff (Req 15.3).

    Parameters
    ----------
    actual:
        The value to compare (will be JSON-serialised).
    snapshot_name:
        Logical name for the snapshot (used as the file stem).
    test_file:
        Path to the test file -- snapshots are stored in
        ``<test_dir>/__snapshots__/<snapshot_name>.snap``.
    update:
        When ``True`` overwrite the stored snapshot unconditionally.
    """
    mgr = SnapshotManager(update=update)
    snap_path = mgr.get_snapshot_path(test_file, snapshot_name)
    stored = mgr.read_snapshot(snap_path)

    if stored is None or update:
        mgr.write_snapshot(snap_path, _serialize(actual))
        return

    actual_ser = _serialize(actual)
    if json.dumps(stored, sort_keys=True, default=str) != json.dumps(
        actual_ser, sort_keys=True, default=str
    ):
        diff = mgr.diff(stored, actual_ser)
        raise MCPAssertionError(
            f"Snapshot mismatch for '{snapshot_name}'",
            diff=diff,
        )
