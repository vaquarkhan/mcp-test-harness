"""MCP inventory coverage tracking for a test run.

Records which tools, resources, and prompts were advertised by the server
versus which were exercised (and which had auth-boundary tests).
"""

from __future__ import annotations

import weakref
from dataclasses import dataclass, field
from typing import Any

_COVERAGE_ATTR = "_mcp_harness_coverage"
_coverage_by_session: weakref.WeakKeyDictionary[Any, CoverageState] = (
    weakref.WeakKeyDictionary()
)


@dataclass
class CoverageState:
    """Mutable coverage counters for one MCP session / worker."""

    advertised_tools: set[str] = field(default_factory=set)
    advertised_resources: set[str] = field(default_factory=set)
    advertised_prompts: set[str] = field(default_factory=set)
    tested_tools: set[str] = field(default_factory=set)
    tested_resources: set[str] = field(default_factory=set)
    tested_prompts: set[str] = field(default_factory=set)
    auth_tested_tools: set[str] = field(default_factory=set)


def _unwrap_session(session: Any) -> Any:
    """Follow TracedSession / ChaosSession ``_inner`` to the real ClientSession.

    Coverage must live on the underlying session: the executor injects a
    per-test wrapper, but the scheduler reads coverage from ``server.session``.
    """
    cur = session
    seen: set[int] = set()
    while True:
        ident = id(cur)
        if ident in seen:
            break
        seen.add(ident)
        try:
            inner = object.__getattribute__(cur, "_inner")
        except AttributeError:
            break
        if inner is None:
            break
        cur = inner
    return cur


def _ensure(session: Any) -> CoverageState:
    session = _unwrap_session(session)
    d = getattr(session, "__dict__", None)
    if isinstance(d, dict) and _COVERAGE_ATTR in d:
        return d[_COVERAGE_ATTR]
    try:
        existing = _coverage_by_session.get(session)
        if existing is not None:
            return existing
    except TypeError:
        pass
    state = CoverageState()
    if isinstance(d, dict):
        try:
            d[_COVERAGE_ATTR] = state
            return state
        except (TypeError, AttributeError):
            pass
    try:
        _coverage_by_session[session] = state
    except TypeError:
        pass
    return state


def get_coverage(session: Any) -> CoverageState:
    """Return the coverage state for *session* (creates if missing)."""
    return _ensure(session)


async def capture_advertised_inventory(session: Any) -> None:
    """Populate advertised tool/resource/prompt sets from the live server."""
    state = _ensure(session)

    def _items(result: Any, attr: str) -> list[Any]:
        if isinstance(result, dict):
            raw = result.get(attr, result.get(attr + "s", []))
        else:
            raw = getattr(result, attr, None) or getattr(result, attr + "s", None)
        if raw is None:
            raw = result if isinstance(result, list) else []
        return list(raw) if isinstance(raw, list) else []

    try:
        for t in _items(await session.list_tools(), "tool"):
            name = getattr(t, "name", None) or (t.get("name") if isinstance(t, dict) else None)
            if name:
                state.advertised_tools.add(str(name))
    except Exception:
        pass
    try:
        for r in _items(await session.list_resources(), "resource"):
            uri = getattr(r, "uri", None) or (r.get("uri") if isinstance(r, dict) else None)
            if uri:
                state.advertised_resources.add(str(uri))
    except Exception:
        pass
    try:
        for p in _items(await session.list_prompts(), "prompt"):
            name = getattr(p, "name", None) or (p.get("name") if isinstance(p, dict) else None)
            if name:
                state.advertised_prompts.add(str(name))
    except Exception:
        pass


def record_tool_call(session: Any, tool_name: str) -> None:
    _ensure(session).tested_tools.add(str(tool_name))


def record_resource_read(session: Any, uri: str) -> None:
    _ensure(session).tested_resources.add(str(uri))


def record_prompt(session: Any, prompt_name: str) -> None:
    _ensure(session).tested_prompts.add(str(prompt_name))


def record_auth_test(session: Any, tool_name: str) -> None:
    state = _ensure(session)
    name = str(tool_name)
    state.auth_tested_tools.add(name)
    state.tested_tools.add(name)


def merge_states(*states: CoverageState) -> CoverageState:
    """Union advertised and tested sets across workers."""
    merged = CoverageState()
    for s in states:
        merged.advertised_tools |= s.advertised_tools
        merged.advertised_resources |= s.advertised_resources
        merged.advertised_prompts |= s.advertised_prompts
        merged.tested_tools |= s.tested_tools
        merged.tested_resources |= s.tested_resources
        merged.tested_prompts |= s.tested_prompts
        merged.auth_tested_tools |= s.auth_tested_tools
    return merged


def coverage_to_dict(state: CoverageState) -> dict[str, Any]:
    """Serialisable coverage report with gap analysis."""
    untested_tools = sorted(state.advertised_tools - state.tested_tools)
    untested_resources = sorted(state.advertised_resources - state.tested_resources)
    untested_prompts = sorted(state.advertised_prompts - state.tested_prompts)
    tools_missing_auth = sorted(state.tested_tools - state.auth_tested_tools)
    return {
        "advertised": {
            "tools": sorted(state.advertised_tools),
            "resources": sorted(state.advertised_resources),
            "prompts": sorted(state.advertised_prompts),
        },
        "tested": {
            "tools": sorted(state.tested_tools),
            "resources": sorted(state.tested_resources),
            "prompts": sorted(state.tested_prompts),
            "auth_tools": sorted(state.auth_tested_tools),
        },
        "gaps": {
            "untested_tools": untested_tools,
            "untested_resources": untested_resources,
            "untested_prompts": untested_prompts,
            "tools_missing_auth_tests": tools_missing_auth,
        },
        "summary": {
            "tools_advertised": len(state.advertised_tools),
            "tools_tested": len(state.tested_tools),
            "tools_untested": len(untested_tools),
            "tools_missing_auth": len(tools_missing_auth),
        },
    }
