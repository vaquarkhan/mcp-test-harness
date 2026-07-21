"""Protocol constants for SEP-2575 / SEP-2243 stateless Streamable HTTP."""

from __future__ import annotations

# JSON-RPC error codes (MCP spec)
UNSUPPORTED_PROTOCOL_VERSION = -32022
MISSING_REQUIRED_CLIENT_CAPABILITY = -32021
INVALID_REQUEST = -32600

# Default draft / RC protocol revision targeted by the harness
DEFAULT_STATELESS_VERSION = "2026-07-28"

# Prior revision still supported by stateful lifecycle + initialize handshake
DEFAULT_STATEFUL_VERSION = "2025-03-26"

META_NS = "io.modelcontextprotocol"
