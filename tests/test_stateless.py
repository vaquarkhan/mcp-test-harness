"""Tests for SEP-2575 stateless conformance and throughput."""

from __future__ import annotations

import json
from typing import Callable
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from mcp_test_harness.assertions import MCPAssertionError, assert_stateless_throughput
from mcp_test_harness.stateless.conformance import (
    ConformanceCheck,
    StatelessConformanceGate,
    stateless_badge_markdown,
)
from mcp_test_harness.stateless.constants import UNSUPPORTED_PROTOCOL_VERSION
from mcp_test_harness.stateless.payloads import (
    build_jsonrpc_request,
    build_stateless_params,
    routing_headers,
)
from mcp_test_harness.stateless.throughput import StatelessThroughputEngine, ThroughputMetrics
from mcp_test_harness.try_cli import run_conformance

Handler = Callable[[httpx.Request], httpx.Response]


def _mock_stateless_handler(request: httpx.Request) -> httpx.Response:
    """Minimal compliant stateless MCP server for adversarial tests."""
    try:
        body = json.loads(request.content)
    except json.JSONDecodeError:
        return httpx.Response(400, json={"error": {"code": -32700, "message": "Parse error"}})

    method = body.get("method")
    hdr_proto = request.headers.get("MCP-Protocol-Version")
    hdr_method = request.headers.get("Mcp-Method")
    meta = (body.get("params") or {}).get("_meta") or {}
    payload_proto = meta.get("io.modelcontextprotocol/protocolVersion")

    if hdr_proto is None:
        return httpx.Response(400, json={"error": {"code": -32600, "message": "missing protocol header"}})

    if hdr_proto != payload_proto:
        return httpx.Response(
            400,
            json={
                "error": {
                    "code": UNSUPPORTED_PROTOCOL_VERSION,
                    "message": "version mismatch",
                    "data": {"supported": ["2026-07-28"], "requested": payload_proto},
                },
            },
        )

    if payload_proto == "9999-99-99":
        return httpx.Response(
            400,
            json={
                "error": {
                    "code": UNSUPPORTED_PROTOCOL_VERSION,
                    "message": "unsupported",
                    "data": {"supported": ["2026-07-28"], "requested": "9999-99-99"},
                },
            },
        )

    if hdr_method is None:
        return httpx.Response(400, json={"error": {"code": -32600, "message": "missing Mcp-Method"}})

    if hdr_method != method:
        return httpx.Response(400, json={"error": {"code": -32600, "message": "method mismatch"}})

    if method == "server/discover":
        return httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "result": {
                    "supportedVersions": ["2026-07-28"],
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "mock", "version": "1.0"},
                },
            },
        )

    if method == "tools/call":
        return httpx.Response(
            200,
            json={"jsonrpc": "2.0", "id": body.get("id"), "result": {"content": []}},
        )

    return httpx.Response(404, json={"error": {"code": -32601, "message": "not found"}})


def _gate_with_handler(url: str, handler: Handler) -> StatelessConformanceGate:
    transport = httpx.MockTransport(handler)
    gate = StatelessConformanceGate(url)

    def _post(payload: dict, headers: dict) -> httpx.Response:
        with httpx.Client(transport=transport) as client:
            return client.post(url, json=payload, headers=headers)

    gate._post = _post  # type: ignore[method-assign]
    return gate


@pytest.fixture
def mock_url() -> str:
    return "http://mock.test/mcp"


def test_build_stateless_params_and_payload():
    params = build_stateless_params(extra={"name": "x"})
    assert params["name"] == "x"
    assert "io.modelcontextprotocol/protocolVersion" in params["_meta"]

    payload = build_jsonrpc_request("server/discover", req_id="custom-id")
    assert payload["id"] == "custom-id"
    assert payload["method"] == "server/discover"


def test_routing_headers_sep2243():
    h = routing_headers(method="tools/call", name="echo", include_method=False, include_protocol=False)
    assert "Mcp-Method" not in h
    assert "MCP-Protocol-Version" not in h
    assert h["Mcp-Name"] == "echo"


def test_stateless_conformance_all_pass(mock_url: str):
    gate = _gate_with_handler(mock_url, _mock_stateless_handler)
    assert gate.run_all() is True
    assert all(r.passed for r in gate.results)
    assert len(gate.results) == 6


def test_baseline_discover_non_200(mock_url: str):
    gate = _gate_with_handler(mock_url, lambda _r: httpx.Response(500, text="boom"))
    gate.test_server_discover_baseline()
    assert gate.results[-1].passed is False


def test_baseline_discover_bad_schema(mock_url: str):
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"result": {"supportedVersions": "not-a-list"}})

    gate = _gate_with_handler(mock_url, handler)
    gate.test_server_discover_baseline()
    assert gate.results[-1].passed is False


def test_missing_protocol_header_not_400(mock_url: str):
    gate = _gate_with_handler(mock_url, lambda _r: httpx.Response(200, json={"result": {}}))
    gate.test_missing_protocol_header()
    assert gate.results[-1].passed is False


def test_unsupported_protocol_error_branches(mock_url: str):
    gate = StatelessConformanceGate(mock_url)

    gate._check_unsupported_protocol_error("t", httpx.Response(500))
    assert gate.results[-1].passed is False

    gate._check_unsupported_protocol_error("t", httpx.Response(400, text="not json"))
    assert "not valid JSON" in gate.results[-1].details

    gate._check_unsupported_protocol_error(
        "t",
        httpx.Response(400, json={"error": {"code": -1}}),
    )
    assert "Expected error code" in gate.results[-1].details

    gate._check_unsupported_protocol_error(
        "t",
        httpx.Response(
            400,
            json={"error": {"code": UNSUPPORTED_PROTOCOL_VERSION, "data": {"requested": "x"}}},
        ),
    )
    assert "supported must be a list" in gate.results[-1].details

    gate._check_unsupported_protocol_error(
        "t",
        httpx.Response(
            400,
            json={
                "error": {
                    "code": UNSUPPORTED_PROTOCOL_VERSION,
                    "data": {"supported": ["a"], "requested": "wrong"},
                },
            },
        ),
        expected_requested="expected",
    )
    assert "error.data.requested" in gate.results[-1].details

    gate._check_unsupported_protocol_error(
        "t",
        httpx.Response(
            400,
            json={
                "error": {
                    "code": UNSUPPORTED_PROTOCOL_VERSION,
                    "data": {"supported": ["a"], "requested": "ok"},
                },
            },
        ),
        expected_requested="ok",
    )
    assert gate.results[-1].passed is True


def test_record_non_json_response(mock_url: str):
    gate = StatelessConformanceGate(mock_url)
    gate._record("x", False, "details", httpx.Response(400, text="plain text error"))
    assert gate.results[-1].server_response == {"raw_text": "plain text error"}


def test_stateless_badge_markdown():
    assert "Stateless" in stateless_badge_markdown()


def test_throughput_metrics_empty_and_populated():
    empty = ThroughputMetrics(latencies_s=[], total_requests=0, errors=0, duration_s=0.0)
    assert empty.rps == 0.0
    assert empty.error_rate == 0.0
    assert empty.p99_ms == 0.0
    assert empty.mean_ms == 0.0

    m = ThroughputMetrics(
        latencies_s=[0.01, 0.02, 0.03, 0.04, 0.05],
        total_requests=5,
        errors=1,
        duration_s=1.0,
    )
    assert m.rps == 5.0
    assert m.error_rate == 20.0
    assert m.p99_ms > 0
    assert m.mean_ms > 0


@pytest.mark.asyncio
async def test_throughput_worker_paths():
    engine = StatelessThroughputEngine("http://mock/mcp", concurrency=1)

    ok_resp = MagicMock()
    ok_resp.status_code = 200
    ok_resp.aread = AsyncMock(return_value=b'{"result":{}}')

    err_status = MagicMock()
    err_status.status_code = 503
    err_status.aread = AsyncMock(return_value=b"")

    err_json = MagicMock()
    err_json.status_code = 200
    err_json.aread = AsyncMock(return_value=b'{"error":{"code":-32603}}')

    client = MagicMock()
    client.post = AsyncMock(side_effect=[ok_resp, err_status, err_json, Exception("network")])

    lats, errs = await engine._worker(client, {}, {}, duration_s=0.05)
    assert len(lats) >= 3
    assert errs >= 3


@pytest.mark.asyncio
async def test_execute_load_integration(mock_url: str):
    transport = httpx.MockTransport(_mock_stateless_handler)
    engine = StatelessThroughputEngine(mock_url, concurrency=2)

    real_cls = httpx.AsyncClient

    def _client_factory(**kwargs: object) -> httpx.AsyncClient:
        timeout = kwargs.get("timeout", 30.0)
        return real_cls(transport=transport, timeout=timeout)  # type: ignore[arg-type]

    with patch.object(httpx, "AsyncClient", side_effect=_client_factory):
        metrics = await engine.execute_load("diagnostic_probe", {}, duration_s=0.05)
    assert metrics.total_requests > 0
    assert metrics.rps > 0


def test_post_via_client(mock_url: str):
    transport = httpx.MockTransport(_mock_stateless_handler)
    gate = StatelessConformanceGate(mock_url)
    with gate._client() as client:
        assert client is not None
    with patch.object(gate, "_client", return_value=httpx.Client(transport=transport)):
        payload = build_jsonrpc_request("server/discover")
        headers = routing_headers(method="server/discover")
        resp = gate._post(payload, headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_assert_stateless_throughput_pass():
    metrics = ThroughputMetrics(
        latencies_s=[0.001] * 100,
        total_requests=100,
        errors=0,
        duration_s=0.1,
    )
    with patch.object(
        StatelessThroughputEngine,
        "execute_load",
        new=AsyncMock(return_value=metrics),
    ):
        await assert_stateless_throughput(
            "http://localhost/mcp",
            "echo",
            {"x": 1},
            min_rps=500,
            max_p99_ms=100,
            max_error_rate=1.0,
        )


@pytest.mark.asyncio
async def test_assert_stateless_throughput_failures():
    metrics = ThroughputMetrics(latencies_s=[0.1], total_requests=1, errors=1, duration_s=10.0)
    with patch.object(
        StatelessThroughputEngine,
        "execute_load",
        new=AsyncMock(return_value=metrics),
    ):
        with pytest.raises(MCPAssertionError, match="RPS"):
            await assert_stateless_throughput("http://localhost/mcp", "echo", {}, min_rps=1000)
        with pytest.raises(MCPAssertionError, match="p99"):
            await assert_stateless_throughput(
                "http://localhost/mcp",
                "echo",
                {},
                max_p99_ms=1,
            )
        with pytest.raises(MCPAssertionError, match="Error rate"):
            await assert_stateless_throughput(
                "http://localhost/mcp",
                "echo",
                {},
                max_error_rate=0.0,
            )


def test_cli_conformance_stateless_help():
    with pytest.raises(SystemExit) as exc:
        run_conformance(["stateless", "--help"])
    assert exc.value.code == 0


def test_cli_conformance_stateless_pass(mock_url: str, capsys):
    gate = _gate_with_handler(mock_url, _mock_stateless_handler)
    with patch(
        "mcp_test_harness.stateless.conformance.StatelessConformanceGate",
        return_value=gate,
    ):
        code = run_conformance(
            ["stateless", "--url", mock_url, "--generate-badge", "--verbose"],
        )
    assert code == 0
    out = capsys.readouterr().out
    assert "SERVER CERTIFIED" in out
    assert "README badge" in out


def test_cli_conformance_stateless_fail(mock_url: str, capsys):
    gate = _gate_with_handler(mock_url, lambda _r: httpx.Response(500))
    with patch(
        "mcp_test_harness.stateless.conformance.StatelessConformanceGate",
        return_value=gate,
    ):
        code = run_conformance(["stateless", "--url", mock_url])
    assert code == 1
    assert "NON-COMPLIANT" in capsys.readouterr().err


def test_conformance_check_dataclass():
    c = ConformanceCheck(True, "n", "d", http_status=200, server_response={"ok": True})
    assert c.passed is True
