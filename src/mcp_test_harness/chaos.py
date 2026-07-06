"""Protocol-aware chaos fault injection for MCP test sessions."""

from __future__ import annotations

import asyncio
import copy
import json
from dataclasses import dataclass, field
from typing import Any

from mcp_test_harness.trace import TraceRecorder, attach_trace


class ChaosFaultError(Exception):
    """Simulated transport or gateway failure."""

    def __init__(self, message: str, *, code: int = 503) -> None:
        super().__init__(message)
        self.code = code


@dataclass
class ChaosConfig:
    """Parsed chaos faults for one test."""

    faults: list[str] = field(default_factory=list)
    delay_ms: float = 0.0
    inject_error: bool = False
    truncate: bool = False
    schema_drift: bool = False


def parse_chaos_from_markers(markers: dict[str, Any]) -> ChaosConfig | None:
    """Build chaos config from ``@marker(tags=[\"chaos\"], chaos_faults=[...])``."""
    tags = list(markers.get("tags") or [])
    raw_faults: list[str] = list(markers.get("chaos_faults") or [])
    for tag in tags:
        if tag.startswith("chaos:"):
            raw_faults.append(tag.split(":", 1)[1])

    if "chaos" not in tags and not raw_faults:
        return None
    if not raw_faults:
        raw_faults = ["delay"]

    cfg = ChaosConfig(faults=raw_faults)
    for fault in raw_faults:
        low = fault.lower()
        if low in ("delay", "slow"):
            cfg.delay_ms = max(cfg.delay_ms, 100.0)
        elif low.startswith("delay_ms:") or low.startswith("delay:"):
            try:
                cfg.delay_ms = max(cfg.delay_ms, float(low.split(":", 1)[1]))
            except ValueError:
                cfg.delay_ms = max(cfg.delay_ms, 100.0)
        elif low in ("503", "error_503", "unavailable", "retry_storm"):
            cfg.inject_error = True
        elif low in ("truncate", "partial", "partial_result"):
            cfg.truncate = True
        elif low in ("schema_drift", "drift", "schema-drift"):
            cfg.schema_drift = True
    return cfg


def _truncate_result(result: Any) -> Any:
    content = getattr(result, "content", None)
    if not content:
        return result
    items = list(content)
    if not items:
        return result
    first = items[0]
    text = getattr(first, "text", None)
    if text is None and isinstance(first, dict):
        text = first.get("text")
    if isinstance(text, str) and len(text) > 8:
        new_text = text[: max(4, len(text) // 2)]
        if hasattr(first, "text"):
            first.text = new_text  # type: ignore[attr-defined]
        elif isinstance(first, dict):
            first["text"] = new_text
    return result


def _drift_result(result: Any) -> Any:
    content = getattr(result, "content", None)
    if not content:
        return result
    for item in content:
        text = getattr(item, "text", None)
        if text is None and isinstance(item, dict):
            text = item.get("text")
        if not isinstance(text, str):
            continue
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            drifted = copy.deepcopy(data)
            if "user_id" in drifted:
                drifted["id"] = drifted.pop("user_id")
            drifted["__chaos_unexpected_nullable"] = None
            new_text = json.dumps(drifted)
            if hasattr(item, "text"):
                item.text = new_text  # type: ignore[attr-defined]
            elif isinstance(item, dict):
                item["text"] = new_text
    return result


class ChaosSession:
    """Wraps a traced session and applies configured faults."""

    def __init__(self, inner: Any, config: ChaosConfig) -> None:
        object.__setattr__(self, "_inner", inner)
        object.__setattr__(self, "_config", config)

    def __getattr__(self, name: str) -> Any:
        inner = object.__getattribute__(self, "_inner")
        attr = getattr(inner, name)
        if name != "call_tool" or not callable(attr):
            return attr
        return self._wrap_call_tool(attr)

    def _wrap_call_tool(self, fn: Any) -> Any:
        async def wrapped(name: str, arguments: dict[str, Any] | None = None, **kwargs: Any) -> Any:
            cfg: ChaosConfig = object.__getattribute__(self, "_config")
            inner = object.__getattribute__(self, "_inner")
            if cfg.inject_error:
                raise ChaosFaultError(
                    "Simulated 503 Service Unavailable (chaos fault)",
                    code=503,
                )
            if cfg.delay_ms > 0:
                await asyncio.sleep(cfg.delay_ms / 1000.0)
            result = await fn(name, arguments or {}, **kwargs)
            if cfg.truncate:
                result = _truncate_result(result)
            if cfg.schema_drift:
                result = _drift_result(result)
            return result

        return wrapped


def wrap_session_for_test(
    session: Any,
    *,
    markers: dict[str, Any],
) -> tuple[Any, TraceRecorder]:
    """Apply tracing and optional chaos; return (session, recorder)."""
    recorder = TraceRecorder()
    traced = attach_trace(session, recorder)
    chaos = parse_chaos_from_markers(markers)
    wrapped: Any = traced
    if chaos is not None:
        wrapped = ChaosSession(traced, chaos)
    # Preserve harness init result on wrapped sessions
    init = getattr(session, "_mcp_harness_init_result", None)
    if init is not None:
        try:
            setattr(wrapped, "_mcp_harness_init_result", init)
        except Exception:  # noqa: BLE001
            pass
    return wrapped, recorder
