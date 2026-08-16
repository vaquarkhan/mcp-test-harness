"""Suite D — deterministic cross-agent / provenance assertions.

Gated path only: quarantine markers, eviction, cross-tenant deny.
Behavioral multi-agent influence evals stay nightly (out of this module).
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

from mcp_test_harness.assertions import MCPAssertionError, _result_error_text, _result_is_error
from mcp_test_harness.coverage import record_resource_read, record_tool_call

DEFAULT_QUARANTINE_MARKERS: tuple[str, ...] = (
    "quarantine",
    "untrusted",
    "untrusted-context",
    "provenance:untrusted",
    "x-mcp-quarantine",
)


def _as_text_blob(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        parts = []
        for k, v in value.items():
            parts.append(str(k))
            parts.append(_as_text_blob(v))
        return " ".join(parts)
    if isinstance(value, (list, tuple)):
        return " ".join(_as_text_blob(v) for v in value)
    return str(value)


def assert_untrusted_context_quarantined(
    resource: Any,
    *,
    markers: Sequence[str] | None = None,
) -> None:
    """Resource / context payload must carry at least one quarantine marker."""
    needles = tuple(m.lower() for m in (markers or DEFAULT_QUARANTINE_MARKERS))
    blob = _as_text_blob(resource).lower()
    if not any(n in blob for n in needles):
        raise MCPAssertionError(
            "Untrusted context not quarantined: no quarantine/provenance marker found "
            f"(looked for {list(needles)[:6]})"
        )


def assert_context_evicted_on_complete(
    session: Mapping[str, Any] | Any,
    *,
    context_keys: Sequence[str] = ("context", "memory", "scratch", "agent_context"),
) -> None:
    """After completion, session must not retain agent context bags."""
    if isinstance(session, Mapping):
        data = session
    else:
        data = getattr(session, "__dict__", {}) or {}
        if hasattr(session, "get_context"):
            try:
                ctx = session.get_context()
                if isinstance(ctx, Mapping):
                    data = {**data, "context": ctx}
            except Exception:
                pass
    retained: list[str] = []
    for key in context_keys:
        if key in data and data[key]:
            retained.append(key)
    # Also check common attribute names
    for key in context_keys:
        if hasattr(session, key) and getattr(session, key):
            val = getattr(session, key)
            if val not in (None, {}, [], ()):
                if key not in retained:
                    retained.append(key)
    if retained:
        raise MCPAssertionError(
            "Context not evicted on complete; retained keys: " + ", ".join(retained)
        )


async def assert_cross_tenant_read_denied(
    session: Any,
    *,
    resource_uri: str,
    tool_name: str | None = None,
    arguments: Mapping[str, Any] | None = None,
) -> None:
    """Cross-tenant resource/tool access must error (deny), not return peer data."""
    if tool_name:
        result = await session.call_tool(tool_name, dict(arguments or {}))
        record_tool_call(session, tool_name)
        if not _result_is_error(result):
            raise MCPAssertionError(
                f"Cross-tenant tool '{tool_name}' was allowed (expected deny); "
                f"body={_result_error_text(result)[:120]!r}"
            )
        return
    result = await session.read_resource(resource_uri)
    record_resource_read(session, resource_uri)
    # read_resource may return contents or raise; treat isError / empty deny markers
    if hasattr(result, "isError") and result.isError:
        return
    if isinstance(result, Mapping) and result.get("isError"):
        return
    text = _as_text_blob(result).lower()
    if any(x in text for x in ("denied", "forbidden", "unauthorized", "quarantine")):
        return
    # If contents present without deny → fail
    contents = getattr(result, "contents", None) or (
        result.get("contents") if isinstance(result, Mapping) else None
    )
    if contents:
        raise MCPAssertionError(
            f"Cross-tenant read of {resource_uri!r} returned contents (expected deny)"
        )
    # No contents and no explicit deny — still fail closed for empty success
    if not _result_is_error(result) and "error" not in text:
        raise MCPAssertionError(
            f"Cross-tenant read of {resource_uri!r} did not deny access"
        )
