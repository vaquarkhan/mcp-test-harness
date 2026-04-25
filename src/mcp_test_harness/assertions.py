"""MCP-specific assertion helpers.

Each helper performs an MCP protocol operation via a client session and
validates the result.  On failure an :class:`MCPAssertionError` is raised
with a diff-style message showing expected vs actual values.
"""

from __future__ import annotations

import asyncio
import difflib
import json
import math
import re
import statistics
import time
import weakref
from pathlib import Path
from typing import Any, Literal

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


_MCP_HARNESS_LIST_TOOLS = "_mcp_harness_list_tools_result"
# Do not store cache on the session object (``__slots__`` / Pydantic sessions reject extra attrs).
_list_tools_result_cache: weakref.WeakKeyDictionary[Any, Any] = weakref.WeakKeyDictionary()


def _stashed_list_tools_result(session: Any) -> Any | None:
    """Read cached ``list_tools`` for *session* (avoids tripping :class:`MagicMock` auto-attrs)."""
    d = getattr(session, "__dict__", None)
    if isinstance(d, dict) and _MCP_HARNESS_LIST_TOOLS in d:
        return d[_MCP_HARNESS_LIST_TOOLS]
    try:
        return _list_tools_result_cache.get(session)
    except TypeError:
        return None


async def _list_tools_cached(session: Any) -> Any:
    """Cache ``list_tools()`` so repeated calls do not hammer the server.

    Uses a :class:`weakref.WeakKeyDictionary` for normal sessions; for
    :class:`unittest.mock.MagicMock` and types that allow it, the result is also stored
    on ``session.__dict__`` so :func:`_stashed_list_tools_result` can read it without
    synthesizing mock children.
    """
    c = _stashed_list_tools_result(session)
    if c is not None:
        return c
    c = await session.list_tools()
    d = getattr(session, "__dict__", None)
    if isinstance(d, dict):
        try:
            d[_MCP_HARNESS_LIST_TOOLS] = c
            return c
        except (TypeError, AttributeError):  # pragma: no cover
            # Non-assignable instance mapping (e.g. frozen/odd __dict__); use WeakKey path.
            pass
    try:
        _list_tools_result_cache[session] = c
    except TypeError:
        pass
    return c


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
        return {k: _serialize(v) for k, v in sorted(value.items())}
    # Duck-type: try common attribute patterns from MCP SDK objects
    if hasattr(value, "__dict__"):
        return {k: _serialize(v) for k, v in value.__dict__.items() if not k.startswith("_")}
    return str(value)


# ---------------------------------------------------------------------------
# assert_tool_call  (Requirement 3.1, 3.4, 3.6)
# ---------------------------------------------------------------------------


def _drop_field_paths(data: Any, field_paths: list[str] | None) -> Any:
    """Remove keys at any depth when they appear in *field_paths* (key names)."""
    if not field_paths:
        return data
    drop = set(field_paths)
    return _drop_keys(data, drop)


def _drop_keys(value: Any, drop: set[str]) -> Any:
    if isinstance(value, dict):
        return {
            k: _drop_keys(v, drop)
            for k, v in value.items()
            if k not in drop
        }
    if isinstance(value, list):
        return [_drop_keys(x, drop) for x in value]
    return value


def _apply_mask_strings(value: Any, patterns: list[re.Pattern[str]] | None) -> Any:
    if not patterns:
        return value
    if isinstance(value, str):
        for pat in patterns:
            value = pat.sub("<masked>", value)
        return value
    if isinstance(value, dict):
        return {k: _apply_mask_strings(v, patterns) for k, v in sorted(value.items())}
    if isinstance(value, list):
        return [_apply_mask_strings(x, patterns) for x in value]
    return value


async def _validate_arguments_against_schema(
    session: Any, tool_name: str, arguments: dict[str, Any]
) -> None:
    try:
        import jsonschema
    except ImportError:  # pragma: no cover
        return  # pragma: no cover
    res = await _list_tools_cached(session)
    tools = getattr(res, "tools", None) or []
    for t in tools:
        n = getattr(t, "name", None)
        if n is None and isinstance(t, dict):
            n = t.get("name")
        if n != tool_name:
            continue
        schema = getattr(t, "inputSchema", None)
        if schema is None and isinstance(t, dict):
            schema = t.get("inputSchema")
        if not isinstance(schema, dict):
            return
        try:
            jsonschema.validate(
                instance=arguments,
                schema=schema,
            )
        except jsonschema.ValidationError as exc:  # type: ignore[attr-defined]
            raise MCPAssertionError(
                f"Arguments for tool '{tool_name}' do not match inputSchema: {exc.message}"
            ) from exc
        return
    return


async def assert_tool_call(
    session: Any,
    tool_name: str,
    arguments: dict[str, Any],
    expected: Any | None = None,
    *,
    validate_against_input_schema: bool = False,
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
    validate_against_input_schema:
        When True, validate *arguments* with ``jsonschema`` against the
        tool's ``inputSchema`` (requires the ``jsonschema`` package).

    Returns
    -------
    The raw result object from ``session.call_tool``.

    Raises
    ------
    MCPAssertionError
        When the tool returns an error or the response does not match
        *expected*.
    """
    if validate_against_input_schema:
        await _validate_arguments_against_schema(session, tool_name, arguments)

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
        An MCP ``ClientSession``. Capabilities are read from
        ``session.server_capabilities``, then ``session.capabilities``, then
        ``session._mcp_harness_init_result`` (from the harness handshake) if
        present.
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
        ir = getattr(session, "_mcp_harness_init_result", None)
        if ir is not None:
            if isinstance(ir, dict):
                caps = ir.get("capabilities")
            else:
                caps = getattr(ir, "capabilities", None)
    if caps is None:
        raise MCPAssertionError(
            "Session has no server capabilities (expected server_capabilities, "
            "capabilities, or _mcp_harness_init_result.capabilities)"
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
    *,
    ignore_fields: list[str] | None = None,
    mask_patterns: list[str] | None = None,
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
    ignore_fields:
        Key names to strip recursively before comparing (e.g. volatile IDs).
    mask_patterns:
        Regex patterns (as strings) applied to all string values for masking
        (matched substrings replaced with ``<masked>``).
    """
    patterns = [re.compile(p) for p in (mask_patterns or [])]
    working = _serialize(actual)
    working = _drop_field_paths(working, ignore_fields)
    working = _apply_mask_strings(working, patterns if patterns else None)

    mgr = SnapshotManager(update=update)
    snap_path = mgr.get_snapshot_path(test_file, snapshot_name)
    stored = mgr.read_snapshot(snap_path)

    if stored is None or update:
        mgr.write_snapshot(snap_path, working)
        return

    stored_adj = _drop_field_paths(_serialize(stored), ignore_fields)
    stored_adj = _apply_mask_strings(stored_adj, patterns if patterns else None)

    if json.dumps(stored_adj, sort_keys=True, default=str) != json.dumps(
        working, sort_keys=True, default=str
    ):
        diff = mgr.diff(stored_adj, working)
        raise MCPAssertionError(
            f"Snapshot mismatch for '{snapshot_name}'",
            diff=diff,
        )


# ---------------------------------------------------------------------------
# assert_tool_list  (Feature 1)
# ---------------------------------------------------------------------------


async def assert_tool_list(
    session: Any,
    expected_tools: list[str],
) -> None:
    """Assert the server exposes at least the given tool names.

    The *expected_tools* list is checked as a **subset** of the actual
    tool names -- extra tools on the server side are allowed.

    Raises
    ------
    MCPAssertionError
        When any expected tool name is missing from the server's tool list.
    """
    result = await _list_tools_cached(session)
    tools = getattr(result, "tools", None) or []
    actual_names = {getattr(t, "name", t) for t in tools}
    expected_set = set(expected_tools)
    missing = expected_set - actual_names
    if missing:
        diff = _diff_values(sorted(expected_set), sorted(actual_names))
        raise MCPAssertionError(
            f"Missing tools: {sorted(missing)}",
            diff=diff,
        )


# ---------------------------------------------------------------------------
# assert_resource_list  (Feature 1)
# ---------------------------------------------------------------------------


async def assert_resource_list(
    session: Any,
    expected_uris: list[str],
) -> None:
    """Assert the server exposes at least the given resource URIs.

    The *expected_uris* list is checked as a **subset** of the actual
    resource URIs -- extra resources on the server side are allowed.

    Raises
    ------
    MCPAssertionError
        When any expected URI is missing from the server's resource list.
    """
    result = await session.list_resources()
    resources = getattr(result, "resources", None) or []
    actual_uris = {str(getattr(r, "uri", r)) for r in resources}
    expected_set = set(expected_uris)
    missing = expected_set - actual_uris
    if missing:
        diff = _diff_values(sorted(expected_set), sorted(actual_uris))
        raise MCPAssertionError(
            f"Missing resources: {sorted(missing)}",
            diff=diff,
        )


# ---------------------------------------------------------------------------
# assert_tool_rejects  (Feature 2)
# ---------------------------------------------------------------------------


async def assert_tool_rejects(
    session: Any,
    tool_name: str,
    arguments: dict,
    error_substring: str | None = None,
) -> None:
    """Assert that a tool call returns an error (isError=True or raises).

    Raises
    ------
    MCPAssertionError
        When the tool call succeeds without error.
    """
    try:
        result = await session.call_tool(tool_name, arguments)
    except Exception as exc:
        # The call raised -- that counts as rejection.
        if error_substring is not None and error_substring not in str(exc):
            raise MCPAssertionError(
                f"Tool '{tool_name}' raised, but message does not contain "
                f"'{error_substring}': {exc}"
            )
        return

    # Check for isError in content items
    content_items = getattr(result, "content", None) or []
    for item in content_items:
        is_error = getattr(item, "isError", False) or (
            isinstance(item, dict) and item.get("isError", False)
        )
        if is_error:
            if error_substring is not None:
                text = getattr(item, "text", None) or (
                    item.get("text") if isinstance(item, dict) else str(item)
                )
                if error_substring not in (text or ""):
                    raise MCPAssertionError(
                        f"Tool '{tool_name}' returned error, but message does "
                        f"not contain '{error_substring}': {text}"
                    )
            return

    raise MCPAssertionError(
        f"Expected tool '{tool_name}' to return an error, but it succeeded"
    )


# ---------------------------------------------------------------------------
# assert_invalid_tool  (Feature 2)
# ---------------------------------------------------------------------------


async def assert_invalid_tool(
    session: Any,
    tool_name: str,
) -> None:
    """Assert that calling a non-existent tool returns an error.

    Raises
    ------
    MCPAssertionError
        When the tool call succeeds without error.
    """
    await assert_tool_rejects(session, tool_name, {})


# ---------------------------------------------------------------------------
# Authorization-focused helpers
# ---------------------------------------------------------------------------


async def assert_tool_denied(
    session: Any,
    tool_name: str,
    arguments: dict[str, Any],
    *,
    error_substring: str | None = None,
) -> None:
    """Assert a protected operation is denied for the provided call context.

    This is an alias with security-oriented naming so tests read clearly for
    auth/RBAC/tenant boundaries (for example "this role must be denied").
    """
    await assert_tool_rejects(
        session,
        tool_name,
        arguments,
        error_substring=error_substring,
    )


async def assert_authorization_boundary(
    session: Any,
    tool_name: str,
    *,
    allowed_arguments: dict[str, Any],
    denied_arguments: dict[str, Any],
    denied_error_substring: str | None = None,
) -> None:
    """Assert one context is allowed and another is denied for one operation.

    This helper is useful for "confused deputy" and per-operation authorization
    checks where the same tool should succeed for one principal and fail for
    another.
    """
    await assert_tool_call(session, tool_name, allowed_arguments)
    await assert_tool_rejects(
        session,
        tool_name,
        denied_arguments,
        error_substring=denied_error_substring,
    )


# ---------------------------------------------------------------------------
# assert_tool_schema
# ---------------------------------------------------------------------------


async def assert_tool_schema(
    session: Any,
    tool_name: str,
    expected_input_schema: dict[str, Any],
) -> None:
    """Assert the tool's ``inputSchema`` exactly matches *expected_input_schema*."""
    res = await _list_tools_cached(session)
    tools = getattr(res, "tools", None) or []
    for t in tools:
        n = getattr(t, "name", None)
        if n is None and isinstance(t, dict):
            n = t.get("name")
        if n != tool_name:
            continue
        isc = getattr(t, "inputSchema", None)
        if isc is None and isinstance(t, dict):
            isc = t.get("inputSchema")
        if not isinstance(isc, dict):
            raise MCPAssertionError(
                f"Tool '{tool_name}' has no dict inputSchema",
            )
        if _serialize(isc) != _serialize(expected_input_schema):
            diff = _diff_values(
                _serialize(expected_input_schema),
                _serialize(isc),
            )
            raise MCPAssertionError(
                f"inputSchema for '{tool_name}' does not match",
                diff=diff,
            )
        return

    raise MCPAssertionError(f"Tool '{tool_name}' not found via list_tools()")


# ---------------------------------------------------------------------------
# assert_protocol_version
# ---------------------------------------------------------------------------


async def assert_protocol_version(
    session: Any,
    expected: str = "2024-11-05",
) -> None:
    """Assert the negotiated MCP ``protocolVersion`` matches *expected*.

    Works when the session was created by the harness, which stashes
    ``session._mcp_harness_init_result`` after ``initialize()``.
    """
    ir: Any = getattr(session, "_mcp_harness_init_result", None)
    if ir is None:
        raise MCPAssertionError(
            "No initialize result on session (expected _mcp_harness_init_result). "
            "Use a harness-managed server or assign it from initialize().",
        )
    pv = getattr(ir, "protocolVersion", None)
    if pv is None and isinstance(ir, dict):
        pv = ir.get("protocolVersion")
    if str(pv) != str(expected):
        diff = _diff_values(expected, pv)
        raise MCPAssertionError(
            f"protocolVersion is {pv!r}, expected {expected!r}",
            diff=diff,
        )


# ---------------------------------------------------------------------------
# assert_tool_idempotent
# ---------------------------------------------------------------------------


async def assert_tool_idempotent(
    session: Any,
    tool_name: str,
    arguments: dict[str, Any],
    *,
    runs: int = 3,
) -> None:
    """Call a tool *runs* times and require identical serialised content each time."""
    first: Any = None
    for _ in range(runs):
        result = await session.call_tool(tool_name, arguments)
        content = getattr(result, "content", None) or result
        ser = _serialize(content)
        if first is None:
            first = ser
        elif ser != first:
            diff = _diff_values(first, ser)
            raise MCPAssertionError(
                f"Tool '{tool_name}' returned differing results across calls",
                diff=diff,
            )


# ---------------------------------------------------------------------------
# assert_latency
# ---------------------------------------------------------------------------

_LatencyAggregate = Literal["max", "p95", "p99", "mean", "median"]


def _aggregate_latency_ms(timings: list[float], aggregate: _LatencyAggregate) -> float:
    """Reduce multiple samples to a single value for budget comparison."""
    if not timings:
        return 0.0
    if aggregate == "max":
        return max(timings)
    if aggregate == "mean":
        return float(statistics.mean(timings))
    if aggregate == "median":
        return float(statistics.median(timings))
    q = 0.95 if aggregate == "p95" else 0.99
    s = sorted(timings)
    n = len(s)
    if n == 1:
        return s[0]
    # Linear interpolation on sorted samples (R7 / Hyndman & Fan type 7)
    pos = (n - 1) * q
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return s[lo]
    w = pos - lo
    return s[lo] * (1 - w) + s[hi] * w


async def assert_latency(
    session: Any,
    tool_name: str,
    arguments: dict[str, Any],
    *,
    max_ms: float,
    runs: int = 1,
    warmup: int = 0,
    aggregate: _LatencyAggregate = "max",
) -> None:
    """Fail if ``call_tool`` latency exceeds a budget (single shot or stats over repeats).

    Use in **performance** / regression tests next to functional checks. Tag tests with
    ``@marker(tags=[\"perf\"])`` and run them selectively with ``mcp-test -m perf``.

    Parameters
    ----------
    max_ms
        Budget in **milliseconds** (after aggregate when ``runs > 1``).
    runs
        Number of **timed** iterations (default ``1`` = same as historical behavior).
    warmup
        Number of **untimed** ``call_tool`` invocations before measuring (JIT / cold start).
    aggregate
        How to combine samples when ``runs > 1``: ``"max"`` (worst case), ``"p95"`` / ``"p99"``,
        ``"mean"``, or ``"median"`` (all in milliseconds from ``perf_counter``).
    """
    for _ in range(warmup):
        await session.call_tool(tool_name, arguments)

    timings: list[float] = []
    for _ in range(max(1, runs)):
        t0 = time.perf_counter()
        await session.call_tool(tool_name, arguments)
        timings.append((time.perf_counter() - t0) * 1000.0)

    value = _aggregate_latency_ms(timings, aggregate) if len(timings) > 1 else timings[0]
    if value > max_ms:
        extra = f" samples={timings!r} aggregate={aggregate!r}" if len(timings) > 1 else ""
        raise MCPAssertionError(
            f"Tool '{tool_name}' latency {value:.1f}ms exceeds budget {max_ms}ms{extra}",
        )


async def assert_throughput(
    session: Any,
    tool_name: str,
    arguments: dict[str, Any],
    *,
    concurrent: int = 4,
    total_calls: int = 16,
    min_rps: float | None = None,
    warmup: int = 0,
) -> None:
    """Run concurrent ``call_tool`` invocations and optionally enforce a minimum RPS.

    Complements :func:`assert_latency` (which targets single-request latency) with a
    **load** check: many overlapping calls, bounded by a semaphore.

    Parameters
    ----------
    concurrent
        Maximum in-flight calls at once (semaphore size).
    total_calls
        Number of ``call_tool`` invocations in the measured window.
    min_rps
        If set, the run fails when ``total_calls / wall_seconds`` is below this value.
    warmup
        Untimed ``call_tool`` calls before the measured burst (single-threaded).
    """
    c = max(1, int(concurrent))
    n = max(1, int(total_calls))

    for _ in range(warmup):
        await session.call_tool(tool_name, arguments)

    sem = asyncio.Semaphore(c)

    async def _one() -> None:
        await session.call_tool(tool_name, arguments)

    async def _bounded() -> None:
        async with sem:
            await _one()

    t0 = time.perf_counter()
    await asyncio.gather(*[_bounded() for _ in range(n)])
    elapsed = time.perf_counter() - t0
    rps = n / elapsed if elapsed > 0 else float("inf")
    if min_rps is not None and rps < float(min_rps):
        raise MCPAssertionError(
            f"Tool '{tool_name}' sustained ~{rps:.2f} req/s; "
            f"minimum {float(min_rps):.2f} req/s (concurrent={c}, n={n}, {elapsed*1000:.1f}ms wall)",
        )


# ---------------------------------------------------------------------------
# assert_tool_call_validates_input
# ---------------------------------------------------------------------------


async def assert_tool_call_validates_input(
    session: Any,
    tool_name: str,
    bad_arguments: dict[str, Any],
    expected_error_substring: str | None = None,
) -> None:
    """Assert the server rejects *bad_arguments* (invalid per server rules)."""
    await assert_tool_rejects(
        session,
        tool_name,
        bad_arguments,
        expected_error_substring,
    )
