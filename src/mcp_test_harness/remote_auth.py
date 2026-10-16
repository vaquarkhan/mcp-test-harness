"""Fail-closed check for Streamable HTTP initialize without credentials.

MCPSTG-AUTHN-01. Sends one ``initialize`` JSON-RPC POST and no
``Authorization`` header. 401, 403, or a JSON-RPC error without a
``protocolVersion`` result passes. A successful handshake fails the gate.
"""

from __future__ import annotations

from typing import Any

import httpx

from mcp_test_harness import __version__
from mcp_test_harness.assertions import MCPAssertionError

_INIT_BODY: dict[str, Any] = {
    "jsonrpc": "2.0",
    "id": "mcpstg-authn-01",
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-03-26",
        "capabilities": {},
        "clientInfo": {"name": "mcp-test-harness", "version": __version__},
    },
}

_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}


def unauthenticated_initialize_reason(status: int, body: Any) -> str | None:
    """Return a failure reason, or None when the response denies the handshake."""
    if status in {401, 403}:
        return None
    if isinstance(body, dict):
        result = body.get("result")
        if isinstance(result, dict) and result.get("protocolVersion"):
            return f"unauthenticated initialize succeeded (HTTP {status})"
        if body.get("error") is not None and result is None:
            return None
    if status >= 400:
        return None
    return f"unauthenticated initialize was not denied (HTTP {status})"


async def assert_remote_requires_auth(
    url: str,
    *,
    client: httpx.AsyncClient | None = None,
    timeout_s: float = 5.0,
) -> None:
    """POST initialize with no credentials. Fail when the server completes the handshake."""
    owns_client = client is None
    http = client or httpx.AsyncClient(timeout=timeout_s)
    try:
        response = await http.post(url, json=_INIT_BODY, headers=_HEADERS)
        try:
            body: Any = response.json()
        except Exception:
            body = response.text
        reason = unauthenticated_initialize_reason(response.status_code, body)
        if reason:
            raise MCPAssertionError(reason)
    finally:
        if owns_client:
            await http.aclose()
