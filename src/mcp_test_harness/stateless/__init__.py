"""SEP-2575 stateless MCP (2026-07-28) — conformance and hyperscale throughput.

Stateful servers continue to use :mod:`mcp_test_harness.lifecycle` and session-based
assertions. Stateless Streamable HTTP servers use this package for adversarial
conformance checks and URL-direct load tests (no ``initialize`` handshake).
"""

from mcp_test_harness.stateless.conformance import (
    ConformanceCheck,
    StatelessConformanceGate,
    stateless_badge_markdown,
)
from mcp_test_harness.stateless.throughput import (
    StatelessThroughputEngine,
    ThroughputMetrics,
)

__all__ = [
    "ConformanceCheck",
    "StatelessConformanceGate",
    "StatelessThroughputEngine",
    "ThroughputMetrics",
    "stateless_badge_markdown",
]
