"""Edge-branch coverage for cyber suite modules."""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_test_harness.assertions import MCPAssertionError
from mcp_test_harness.assurance_reports import build_trust_boundary_matrix
from mcp_test_harness.audit_chain import run_audit_verify
from mcp_test_harness.endpoint_evidence import (
    assert_endpoint_finding_ingested,
    load_numbat_findings,
    map_numbat_finding,
)
from mcp_test_harness.evidence import (
    matrix_to_dicts,
    out_of_band_coverage_row,
    record_from_counts,
)
from mcp_test_harness.incident_conformance import (
    assert_benchmark_egress_denied,
    assert_command_injection_blocked,
    assert_path_symlink_escape_blocked,
    assert_url_exfil_bounded,
)
from mcp_test_harness.load_resilience import (
    LoadCallOutcome,
    LoadResilienceReport,
    assert_control_engages_under_load,
    assert_fairness_under_load,
    assert_latency_slo_until_shed,
    assert_no_fail_open_under_load,
    classify_load_failure,
    collect_load_resilience,
)
from mcp_test_harness.metrics import (
    adaptive_success_rate,
    control_effectiveness,
    detection_rate,
    false_positive_rate,
)
from mcp_test_harness.oscal import build_assessment_results, validate_assessment_results
from mcp_test_harness.schema_rules import (
    destructive_without_constraints,
    evaluate_schema_precondition_rules,
    find_unbounded_string_params,
)
from mcp_test_harness.suite_d import (
    _as_text_blob,
    assert_context_evicted_on_complete,
    assert_cross_tenant_read_denied,
)


def test_blob_and_matrix_and_metrics() -> None:
    assert _as_text_blob(None) == ""
    assert "a" in _as_text_blob([1, {"a": 2}])
    build_trust_boundary_matrix()
    matrix_to_dicts([out_of_band_coverage_row()])
    assert adaptive_success_rate(attacks=4, successes=1) == 0.25
    assert detection_rate(attacks=0, detected=1) == 0.0
    assert false_positive_rate(benign=4, flagged=1) == 0.25
    a = record_from_counts(control_id="c", suite="s", passed=1, failed=0, gated=True)
    b = record_from_counts(control_id="c", suite="s2", passed=0, failed=1, gated=True)
    assert control_effectiveness([a, b])["controls"]["c"] == "proven"


def test_suite_d_get_context_and_schema_edges() -> None:
    class S:
        def get_context(self):
            return {"x": 1}

    with pytest.raises(MCPAssertionError):
        assert_context_evicted_on_complete(S())

    class S2:
        def get_context(self):
            raise RuntimeError("x")

    assert_context_evicted_on_complete(S2())
    findings = evaluate_schema_precondition_rules(
        [
            {"name": "t", "inputSchema": {"properties": "bad"}},
            {"name": "t2", "inputSchema": {"properties": {"x": "not-map"}}},
            {
                "name": "delete_x",
                "inputSchema": {
                    "properties": {
                        "a": {"type": "string", "enum": ["1"]},
                        "b": {"title": "Confirm"},
                    }
                },
            },
            {"name": "shell_x", "inputSchema": {}},
            {"name": "exec", "inputSchema": {"properties": {}}},
        ]
    )
    assert findings


def test_endpoint_map_and_oscal_audit_cli(tmp_path: Path) -> None:
    m = map_numbat_finding({"title": "x"})
    assert m["mitre"] == []
    with pytest.raises(MCPAssertionError):
        assert_endpoint_finding_ingested({"title": "x", "mitre": None})
    with patch(
        "mcp_test_harness.endpoint_evidence.map_numbat_finding",
        return_value={"source": "other", "out_of_band": True, "mitre": []},
    ):
        with pytest.raises(MCPAssertionError, match="numbat"):
            assert_endpoint_finding_ingested({})
    with patch(
        "mcp_test_harness.endpoint_evidence.map_numbat_finding",
        return_value={"source": "numbat", "out_of_band": False, "mitre": []},
    ):
        with pytest.raises(MCPAssertionError, match="out_of_band"):
            assert_endpoint_finding_ingested({})
    with pytest.raises(ValueError):
        build_assessment_results("nope")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        validate_assessment_results(
            {
                "assessment-results": {
                    "uuid": "u",
                    "metadata": {"title": "t"},
                    "results": "bad",
                }
            }
        )
    with pytest.raises(SystemExit):
        run_audit_verify([])
    p = tmp_path / "n.ndjson"
    p.write_text('\n{"title": "a", "mitre": []}\n\n', encoding="utf-8")
    assert len(load_numbat_findings(p)) == 1


@pytest.mark.asyncio
async def test_remaining_and_load_incident_edges() -> None:
    assert find_unbounded_string_params({"name": "t", "inputSchema": "nope"}) == []
    assert destructive_without_constraints({"name": "delete", "inputSchema": 1}) is True
    assert (
        destructive_without_constraints(
            {
                "name": "delete",
                "inputSchema": {
                    "properties": {
                        "x": "bad",
                        "y": {"title": "Confirm", "type": "string"},
                    }
                },
            }
        )
        is False
    )

    class Sess:
        @property
        def memory(self):
            return {"x": 1}

    with pytest.raises(MCPAssertionError, match="memory"):
        assert_context_evicted_on_complete(Sess())

    s = MagicMock()
    s.read_resource = AsyncMock(
        return_value=SimpleNamespace(isError=True, contents=None)
    )
    await assert_cross_tenant_read_denied(s, resource_uri="r")
    s.call_tool = AsyncMock(side_effect=RuntimeError("x"))
    await assert_command_injection_blocked(s, "e", payloads=["; id"])
    await assert_url_exfil_bounded(s, "u", payloads=["http://x"])
    with patch(
        "mcp_test_harness.load_resilience.asyncio.wait_for",
        side_effect=asyncio.TimeoutError,
    ):
        rep = await collect_load_resilience(s, "t", concurrent=1, total_calls=1)
    assert rep.kind_counts.get("timeout", 0) >= 1

    assert classify_load_failure(raised=asyncio.TimeoutError())[0] == "timeout"
    sa, sb = MagicMock(), MagicMock()

    async def deny(*_a, **_k):
        return SimpleNamespace(
            isError=True, content=[SimpleNamespace(text="RATE_LIMITED")]
        )

    async def slow_ok(*_a, **_k):
        await asyncio.sleep(0.05)
        return SimpleNamespace(isError=False, content=[])

    sa.call_tool = deny
    sb.call_tool = slow_ok
    with pytest.raises(MCPAssertionError, match="SLO"):
        await assert_fairness_under_load(
            sa, sb, tool_name="t", concurrent=1, total_calls=2, max_p99_ms_b=0.001
        )
    s.call_tool = slow_ok
    with pytest.raises(MCPAssertionError, match="p99"):
        await assert_latency_slo_until_shed(
            s, "t", concurrent=1, total_calls=3, max_p99_ms=0.001
        )
    bad = LoadResilienceReport(
        outcomes=[
            LoadCallOutcome(
                ok=False, error_kind="exception", deny_code="RATE_LIMITED"
            )
        ]
    )
    with patch(
        "mcp_test_harness.load_resilience._run_classified_burst",
        new_callable=AsyncMock,
        return_value=bad,
    ):
        with pytest.raises(MCPAssertionError, match="mislabeled"):
            await assert_no_fail_open_under_load(
                s,
                "t",
                phases=[
                    {
                        "name": "w",
                        "concurrent": 1,
                        "total_calls": 1,
                        "warmup": True,
                    }
                ],
            )
    mixed = LoadResilienceReport(
        outcomes=[
            LoadCallOutcome(ok=False, error_kind="timeout"),
            LoadCallOutcome(ok=False, error_kind="timeout"),
            LoadCallOutcome(ok=False, error_kind="deny", deny_code="RATE_LIMITED"),
        ]
    )
    with patch(
        "mcp_test_harness.load_resilience.collect_load_resilience",
        new_callable=AsyncMock,
        return_value=mixed,
    ):
        with pytest.raises(MCPAssertionError, match="timeout/exception"):
            await assert_control_engages_under_load(
                s, "t", expect_deny_code="RATE_LIMITED", total_calls=1
            )
    s.call_tool = AsyncMock(
        return_value=SimpleNamespace(
            isError=False, content=[SimpleNamespace(text="ok")]
        )
    )
    with pytest.raises(MCPAssertionError, match="accepted"):
        await assert_path_symlink_escape_blocked(s, "r", payloads=["../x"])
    with pytest.raises(MCPAssertionError, match="without deny"):
        await assert_command_injection_blocked(s, "e", payloads=["; id"])
    s.call_tool = AsyncMock(
        return_value=SimpleNamespace(
            isError=True, content=[SimpleNamespace(text="nope")]
        )
    )
    await assert_benchmark_egress_denied(s, "f")
