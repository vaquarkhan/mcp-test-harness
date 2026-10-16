"""Deterministic URL-fetch policy for tool arguments (MCPSTG-GW-02).

Classifies a URL the server should refuse before any DNS lookup: disallowed
schemes, userinfo, missing hosts, and literal non-public addresses. This is
not a live SSRF or DNS-rebinding exercise.
"""

from __future__ import annotations

import ipaddress
from typing import Any, Sequence
from urllib.parse import urlparse

from mcp_test_harness.assertions import MCPAssertionError, _result_is_error
from mcp_test_harness.coverage import record_tool_call

_METADATA_HOSTS = frozenset({"metadata.google.internal"})

# Lab placeholders only. Every entry must classify as unsafe.
UNSAFE_URL_CORPUS: tuple[str, ...] = (
    "file:///tmp/lab",
    "data:text/plain,lab",
    "gopher://127.0.0.1/",
    "https://user:pass@example.invalid/hook",
    "https://",
    "https://127.0.0.1/latest",
    "https://[::1]/",
    "https://169.254.169.254/latest/meta-data/",
    "https://10.1.2.3/",
    "https://metadata.google.internal/computeMetadata/v1/",
    "http://example.invalid/fetch",
    "https://224.0.0.1/",
    "https://0.0.0.0/",
    "https://240.0.0.1/",
)


def classify_fetch_url(url: str) -> str | None:
    """Return a deny reason, or None when the URL is an https name with a public host.

    Literal IP checks do not resolve DNS. A hostname that later points at a
    private address is out of scope for this gate.
    """
    raw = str(url).strip()
    if not raw:
        return "empty-url"
    parsed = urlparse(raw)
    scheme = (parsed.scheme or "").lower()
    if scheme not in {"http", "https"}:
        return f"disallowed-scheme:{scheme or 'missing'}"
    if parsed.username or parsed.password:
        return "userinfo"
    host = (parsed.hostname or "").rstrip(".").lower()
    if not host:
        return "missing-host"
    if host in _METADATA_HOSTS:
        return "metadata-hostname"
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    if ip is not None and (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    ):
        return "non-public-address"
    if scheme != "https":
        return "insecure-scheme"
    return None


async def assert_unsafe_url_fetch_blocked(
    session: Any,
    tool_name: str,
    *,
    argument_name: str = "url",
    payloads: Sequence[str] | None = None,
) -> None:
    """Each unsafe URL must error or raise. A successful tool result fails the gate."""
    corpus = list(payloads) if payloads is not None else list(UNSAFE_URL_CORPUS)
    failures: list[str] = []
    for payload in corpus:
        try:
            result = await session.call_tool(tool_name, {argument_name: payload})
        except Exception:
            continue
        if _result_is_error(result):
            continue
        reason = classify_fetch_url(payload) or "unsafe"
        failures.append(f"{reason} accepted: {payload!r}")
    record_tool_call(session, tool_name)
    if failures:
        raise MCPAssertionError(
            f"Unsafe URL fetch policy failed ({len(failures)}):\n"
            + "\n".join(f"  - {item}" for item in failures[:10])
        )
