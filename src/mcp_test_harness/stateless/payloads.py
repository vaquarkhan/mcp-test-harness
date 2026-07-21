"""JSON-RPC payload builders for stateless MCP requests."""

from __future__ import annotations

from typing import Any

from mcp_test_harness import __version__
from mcp_test_harness.stateless.constants import DEFAULT_STATELESS_VERSION, META_NS


def build_stateless_params(
    *,
    protocol_version: str = DEFAULT_STATELESS_VERSION,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build ``params`` with mandatory ``_meta`` for SEP-2575 stateless calls."""
    params: dict[str, Any] = {
        "_meta": {
            f"{META_NS}/protocolVersion": protocol_version,
            f"{META_NS}/clientInfo": {
                "name": "mcp-test-harness",
                "version": __version__,
            },
            f"{META_NS}/clientCapabilities": {},
        },
    }
    if extra:
        params.update(extra)
    return params


def build_jsonrpc_request(
    method: str,
    *,
    protocol_version: str = DEFAULT_STATELESS_VERSION,
    params_extra: dict[str, Any] | None = None,
    req_id: str | None = None,
) -> dict[str, Any]:
    """Self-contained JSON-RPC 2.0 request for stateless HTTP POST."""
    return {
        "jsonrpc": "2.0",
        "id": req_id or f"stateless-{method.replace('/', '-')}",
        "method": method,
        "params": build_stateless_params(
            protocol_version=protocol_version,
            extra=params_extra,
        ),
    }


def routing_headers(
    *,
    method: str,
    protocol_version: str = DEFAULT_STATELESS_VERSION,
    name: str | None = None,
    include_method: bool = True,
    include_protocol: bool = True,
) -> dict[str, str]:
    """SEP-2243 routing headers for Streamable HTTP POST."""
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if include_protocol:
        headers["MCP-Protocol-Version"] = protocol_version
    if include_method:
        headers["Mcp-Method"] = method
    if name is not None:
        headers["Mcp-Name"] = name
    return headers
