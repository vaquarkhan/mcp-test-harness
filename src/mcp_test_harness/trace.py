"""MCP JSON-RPC trace capture for per-test diagnostics and HTML timelines."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

# Methods we instrument on the client session (MCP SDK surface).
_TRACED_METHODS = frozenset(
    {
        "initialize",
        "list_tools",
        "call_tool",
        "list_resources",
        "read_resource",
        "list_prompts",
        "get_prompt",
    }
)


def _safe_json(obj: Any, *, limit: int = 4000) -> Any:
    """Best-effort JSON-serialisable summary of *obj*."""
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        s = str(obj)
        return s if len(s) <= limit else s[: limit - 1] + "…"
    if isinstance(obj, dict):
        return {str(k): _safe_json(v, limit=limit // max(1, len(obj))) for k, v in list(obj.items())[:32]}
    if isinstance(obj, (list, tuple)):
        return [_safe_json(v, limit=limit // max(1, len(obj))) for v in list(obj)[:32]]
    if hasattr(obj, "model_dump"):
        try:
            return _safe_json(obj.model_dump(), limit=limit)
        except Exception:  # noqa: BLE001
            pass
    if hasattr(obj, "__dict__"):
        return _safe_json(vars(obj), limit=limit)
    text = repr(obj)
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _payload_bytes(payload: Any) -> int:
    try:
        return len(json.dumps(_safe_json(payload), default=str))
    except Exception:  # noqa: BLE001
        return 0


def _stdio_pollution_hint(exc: BaseException) -> str | None:
    msg = str(exc).lower()
    hints = (
        "json",
        "decode",
        "invalid",
        "unexpected token",
        "stdout",
        "parse",
    )
    if any(h in msg for h in hints):
        return str(exc)
    return None


@dataclass
class TraceRecorder:
    """Collects ordered MCP call events for one test execution."""

    events: list[dict[str, Any]] = field(default_factory=list)
    stdio_pollution: list[str] = field(default_factory=list)
    _start: float = field(default_factory=time.monotonic, repr=False)

    def _offset_ms(self) -> float:
        return round((time.monotonic() - self._start) * 1000.0, 2)

    def record_request(self, method: str, params: Any) -> None:
        self.events.append(
            {
                "t_ms": self._offset_ms(),
                "direction": "request",
                "method": method,
                "payload": _safe_json(params),
                "bytes": _payload_bytes(params),
            }
        )

    def record_response(self, method: str, result: Any) -> None:
        self.events.append(
            {
                "t_ms": self._offset_ms(),
                "direction": "response",
                "method": method,
                "payload": _safe_json(result),
                "bytes": _payload_bytes(result),
            }
        )

    def record_error(self, method: str, exc: BaseException) -> None:
        hint = _stdio_pollution_hint(exc)
        if hint and hint not in self.stdio_pollution:
            self.stdio_pollution.append(hint)
        self.events.append(
            {
                "t_ms": self._offset_ms(),
                "direction": "error",
                "method": method,
                "payload": {"error": str(exc), "type": type(exc).__name__},
                "bytes": 0,
                "stdio_pollution": hint is not None,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_count": len(self.events),
            "events": self.events,
            "stdio_pollution": list(self.stdio_pollution),
        }


class TracedSession:
    """Proxy around ``ClientSession`` that records MCP method calls."""

    def __init__(self, inner: Any, recorder: TraceRecorder) -> None:
        object.__setattr__(self, "_inner", inner)
        object.__setattr__(self, "_recorder", recorder)

    def __getattr__(self, name: str) -> Any:
        inner = object.__getattribute__(self, "_inner")
        attr = getattr(inner, name)
        if name not in _TRACED_METHODS or not callable(attr):
            return attr
        return self._wrap_method(name, attr)

    def _wrap_method(self, rpc_name: str, fn: Any) -> Any:
        async def wrapped(*args: Any, **kwargs: Any) -> Any:
            recorder: TraceRecorder = object.__getattribute__(self, "_recorder")
            inner = object.__getattribute__(self, "_inner")
            params: dict[str, Any] = {"args": list(args), "kwargs": kwargs}
            recorder.record_request(rpc_name, params)
            try:
                result = await fn(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001
                recorder.record_error(rpc_name, exc)
                raise
            recorder.record_response(rpc_name, result)
            return result

        return wrapped


def attach_trace(inner: Any, recorder: TraceRecorder) -> TracedSession:
    """Return a session proxy that writes to *recorder*."""
    return TracedSession(inner, recorder)
