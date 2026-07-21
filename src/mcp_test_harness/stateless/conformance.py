"""SEP-2575 / SEP-2243 adversarial conformance suite for stateless Streamable HTTP."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from mcp_test_harness.stateless.constants import (
    DEFAULT_STATELESS_VERSION,
    UNSUPPORTED_PROTOCOL_VERSION,
)
from mcp_test_harness.stateless.payloads import (
    build_jsonrpc_request,
    routing_headers,
)

logger = logging.getLogger(__name__)


@dataclass
class ConformanceCheck:
    """Outcome of a single stateless conformance assertion."""

    passed: bool
    test_name: str
    details: str
    http_status: int | None = None
    server_response: dict[str, Any] | None = None


def stateless_badge_markdown() -> str:
    """README shields.io badge after passing ``mcp-test conformance stateless``."""
    return (
        "![MCP Stateless Compliant]"
        "(https://img.shields.io/badge/MCP_Stateless-Compliant-brightgreen?style=for-the-badge)"
    )


class StatelessConformanceGate:
    """Adversarial SEP-2575 + SEP-2243 validation matrix (HTTP POST only)."""

    def __init__(
        self,
        target_url: str,
        *,
        protocol_version: str = DEFAULT_STATELESS_VERSION,
        timeout: float = 15.0,
    ) -> None:
        self.target_url = target_url.rstrip("/") if target_url.endswith("/mcp/") else target_url
        self.protocol_version = protocol_version
        self.timeout = timeout
        self.results: list[ConformanceCheck] = []

    def _client(self):
        import httpx

        return httpx.Client(timeout=self.timeout)

    def run_all(self) -> bool:
        """Run the full matrix; return True when every check passes."""
        self.results = []
        logger.info("SEP-2575 stateless conformance against %s", self.target_url)

        self.test_server_discover_baseline()
        self.test_missing_protocol_header()
        self.test_mismatched_protocol_version()
        self.test_unsupported_protocol_version_schema()
        self.test_sep2243_missing_mcp_method()
        self.test_sep2243_mismatched_mcp_method()

        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)
        logger.info("Stateless conformance: %s/%s checks passed", passed, total)
        return passed == total

    def _record(
        self,
        name: str,
        passed: bool,
        details: str,
        response: Any = None,
    ) -> None:
        resp_json: dict[str, Any] | None = None
        status: int | None = None
        if response is not None:
            status = response.status_code
            try:
                resp_json = response.json()
            except Exception:
                resp_json = {"raw_text": response.text[:2000]}
        self.results.append(
            ConformanceCheck(
                passed=passed,
                test_name=name,
                details=details,
                http_status=status,
                server_response=resp_json,
            ),
        )
        mark = "PASS" if passed else "FAIL"
        logger.info("[%s] %s: %s", mark, name, details)

    def _post(
        self,
        payload: dict[str, Any],
        headers: dict[str, str],
    ) -> Any:
        with self._client() as client:
            return client.post(self.target_url, json=payload, headers=headers)

    def test_server_discover_baseline(self) -> None:
        """``server/discover`` without prior ``initialize`` handshake."""
        payload = build_jsonrpc_request("server/discover", protocol_version=self.protocol_version)
        headers = routing_headers(method="server/discover", protocol_version=self.protocol_version)
        resp = self._post(payload, headers)

        if resp.status_code != 200:
            self._record(
                "Baseline Discover",
                False,
                f"Expected HTTP 200, got {resp.status_code}",
                resp,
            )
            return

        data = resp.json()
        result = data.get("result") or {}
        ok = isinstance(result.get("supportedVersions"), list) and isinstance(
            result.get("capabilities"),
            dict,
        )
        self._record(
            "Baseline Discover",
            ok,
            "Valid DiscoverResult schema (supportedVersions + capabilities)."
            if ok
            else "Missing supportedVersions or capabilities in result.",
            resp,
        )

    def test_missing_protocol_header(self) -> None:
        payload = build_jsonrpc_request("server/discover", protocol_version=self.protocol_version)
        headers = routing_headers(
            method="server/discover",
            include_protocol=False,
        )
        resp = self._post(payload, headers)
        self._record(
            "Missing Protocol Header",
            resp.status_code == 400,
            f"Expected HTTP 400, got {resp.status_code}",
            resp,
        )

    def test_mismatched_protocol_version(self) -> None:
        payload = build_jsonrpc_request("server/discover", protocol_version=self.protocol_version)
        headers = routing_headers(
            method="server/discover",
            protocol_version="2025-06-18",
        )
        resp = self._post(payload, headers)
        self._check_unsupported_protocol_error("Mismatched Protocol Version", resp)

    def test_unsupported_protocol_version_schema(self) -> None:
        bad = "9999-99-99"
        payload = build_jsonrpc_request("server/discover", protocol_version=bad)
        headers = routing_headers(method="server/discover", protocol_version=bad)
        resp = self._post(payload, headers)
        self._check_unsupported_protocol_error(
            "Unsupported Protocol Version Schema",
            resp,
            expected_requested=bad,
        )

    def test_sep2243_missing_mcp_method(self) -> None:
        payload = build_jsonrpc_request(
            "tools/call",
            protocol_version=self.protocol_version,
            params_extra={"name": "diagnostic_probe", "arguments": {}},
        )
        headers = routing_headers(
            method="tools/call",
            protocol_version=self.protocol_version,
            name="diagnostic_probe",
            include_method=False,
        )
        resp = self._post(payload, headers)
        self._record(
            "SEP-2243 Missing Mcp-Method",
            resp.status_code == 400,
            f"Expected HTTP 400, got {resp.status_code}",
            resp,
        )

    def test_sep2243_mismatched_mcp_method(self) -> None:
        payload = build_jsonrpc_request(
            "tools/call",
            protocol_version=self.protocol_version,
            params_extra={"name": "diagnostic_probe", "arguments": {}},
        )
        headers = routing_headers(
            method="resources/read",
            protocol_version=self.protocol_version,
            name="diagnostic_probe",
        )
        resp = self._post(payload, headers)
        self._record(
            "SEP-2243 Mismatched Mcp-Method",
            resp.status_code == 400,
            f"Expected HTTP 400, got {resp.status_code}",
            resp,
        )

    def _check_unsupported_protocol_error(
        self,
        test_name: str,
        resp: Any,
        *,
        expected_requested: str | None = None,
    ) -> None:
        if resp.status_code != 400:
            self._record(test_name, False, f"Expected HTTP 400, got {resp.status_code}", resp)
            return
        try:
            data = resp.json()
        except json.JSONDecodeError:
            self._record(test_name, False, "Response was not valid JSON", resp)
            return

        error = data.get("error") or {}
        code = error.get("code")
        if code != UNSUPPORTED_PROTOCOL_VERSION:
            self._record(
                test_name,
                False,
                f"Expected error code {UNSUPPORTED_PROTOCOL_VERSION}, got {code!r}",
                resp,
            )
            return

        err_data = error.get("data") or {}
        supported = err_data.get("supported")
        requested = err_data.get("requested")
        if not isinstance(supported, list):
            self._record(test_name, False, "error.data.supported must be a list", resp)
            return
        if expected_requested is not None and requested != expected_requested:
            self._record(
                test_name,
                False,
                f"error.data.requested expected {expected_requested!r}, got {requested!r}",
                resp,
            )
            return
        self._record(
            test_name,
            True,
            "Compliant -32022 UNSUPPORTED_PROTOCOL_VERSION schema.",
            resp,
        )
