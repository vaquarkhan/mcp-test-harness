"""Hyperscale async throughput for stateless Streamable HTTP (SEP-2575)."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any

from mcp_test_harness.assertions import _aggregate_latency_ms
from mcp_test_harness.stateless.constants import DEFAULT_STATELESS_VERSION
from mcp_test_harness.stateless.payloads import build_jsonrpc_request, routing_headers

logger = logging.getLogger(__name__)


@dataclass
class ThroughputMetrics:
    """Aggregated load-test statistics."""

    latencies_s: list[float]
    total_requests: int
    errors: int
    duration_s: float

    @property
    def rps(self) -> float:
        return self.total_requests / self.duration_s if self.duration_s > 0 else 0.0

    @property
    def error_rate(self) -> float:
        if self.total_requests <= 0:
            return 0.0
        return (self.errors / self.total_requests) * 100.0

    @property
    def p99_ms(self) -> float:
        if not self.latencies_s:
            return 0.0
        ms = [x * 1000.0 for x in self.latencies_s]
        return _aggregate_latency_ms(ms, "p99")

    @property
    def mean_ms(self) -> float:
        if not self.latencies_s:
            return 0.0
        ms = [x * 1000.0 for x in self.latencies_s]
        return _aggregate_latency_ms(ms, "mean")


class StatelessThroughputEngine:
    """Protocol-aware concurrent load without ``initialize`` / session state."""

    def __init__(self, target_url: str, *, concurrency: int = 100) -> None:
        self.target_url = target_url
        self.concurrency = max(1, int(concurrency))

    async def _worker(
        self,
        client: Any,
        payload: dict[str, Any],
        headers: dict[str, str],
        duration_s: float,
    ) -> tuple[list[float], int]:
        latencies: list[float] = []
        errors = 0
        end = time.monotonic() + duration_s

        while time.monotonic() < end:
            t0 = time.perf_counter()
            try:
                resp = await client.post(self.target_url, json=payload, headers=headers)
                body = await resp.aread()
                if resp.status_code != 200:
                    errors += 1
                elif b'"error":' in body:
                    errors += 1
            except Exception:
                errors += 1
            latencies.append(time.perf_counter() - t0)

        return latencies, errors

    async def execute_load(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        duration_s: float,
        *,
        protocol_version: str = DEFAULT_STATELESS_VERSION,
    ) -> ThroughputMetrics:
        """Sustain concurrent ``tools/call`` POSTs for *duration_s* seconds."""
        import httpx

        payload = build_jsonrpc_request(
            "tools/call",
            protocol_version=protocol_version,
            params_extra={"name": tool_name, "arguments": arguments},
        )
        headers = routing_headers(
            method="tools/call",
            protocol_version=protocol_version,
            name=tool_name,
        )

        logger.info(
            "Stateless throughput: tool=%r concurrency=%s duration=%ss",
            tool_name,
            self.concurrency,
            duration_s,
        )

        limits = httpx.Limits(max_connections=self.concurrency, max_keepalive_connections=self.concurrency)
        all_latencies: list[float] = []
        total_errors = 0
        t0 = time.perf_counter()

        async with httpx.AsyncClient(limits=limits, timeout=30.0) as client:
            tasks = [
                self._worker(client, payload, headers, duration_s)
                for _ in range(self.concurrency)
            ]
            results = await asyncio.gather(*tasks)
            for lats, errs in results:
                all_latencies.extend(lats)
                total_errors += errs

        elapsed = time.perf_counter() - t0
        metrics = ThroughputMetrics(
            latencies_s=all_latencies,
            total_requests=len(all_latencies),
            errors=total_errors,
            duration_s=elapsed,
        )
        logger.info(
            "Stateless throughput done: %s req @ %.2f RPS (%.2f%% errors)",
            metrics.total_requests,
            metrics.rps,
            metrics.error_rate,
        )
        return metrics
