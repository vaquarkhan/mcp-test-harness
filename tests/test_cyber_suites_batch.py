"""Suite D + attestation + capacity/media + authz + schema + endpoint + assurance."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_test_harness.assertions import MCPAssertionError
from mcp_test_harness.assurance_reports import (
    build_launch_gate_readiness,
    build_trust_boundary_matrix,
)
from mcp_test_harness.attestation import (
    assert_envelope_verified,
    assert_tampered_request_rejected,
    assert_tool_allowlist_deny_by_default,
    assert_unattested_allowed_when_not_required,
    assert_unattested_denied_when_required,
    assert_unattested_server_denied,
    assert_unauthorized_sampling_dropped,
    evaluate_attestation_decision,
)
from mcp_test_harness.authz_conformance import (
    assert_authorization_not_exposure,
    assert_enforcement_decision_recorded,
    assert_hook_fails_closed_on_decision_unreachable,
    assert_hook_fails_closed_on_no_rule,
    assert_hook_fails_closed_on_unknown_server,
    assert_no_token_passthrough,
    assert_over_privileged_enumeration_denied,
    assert_scope_audience_bound,
    assert_scope_bounded_by_owner,
    assert_scope_denies_out_of_scope_server,
    assert_scope_expires,
    assert_token_audience_validated,
)
from mcp_test_harness.endpoint_evidence import (
    assert_endpoint_finding_ingested,
    assert_endpoint_finding_not_governed,
    assert_out_of_band_marked_in_scope_false,
    load_numbat_findings,
)
from mcp_test_harness.evidence import (
    CoverageMatrixEntry,
    out_of_band_coverage_row,
    record_from_counts,
    records_to_dicts,
)
from mcp_test_harness.metrics import (
    adaptive_success_rate,
    control_effectiveness,
    detection_rate,
    false_positive_rate,
    owasp_coverage,
    suite_pass_rate,
)
from mcp_test_harness.oscal import assessment_results_json, build_assessment_results, validate_assessment_results
from mcp_test_harness.schema_rules import assert_schema_preconditions_clean, evaluate_schema_precondition_rules
from mcp_test_harness.suite_b_capacity import (
    assert_capacity_enforced,
    assert_signed_media_exempt,
    assert_unsigned_media_suspect,
    mark_unsigned_suspect_fixture,
    sign_media_fixture,
)
from mcp_test_harness.suite_d import (
    assert_context_evicted_on_complete,
    assert_cross_tenant_read_denied,
    assert_untrusted_context_quarantined,
)


def test_suite_d_quarantine_and_evict() -> None:
    assert_untrusted_context_quarantined({"tags": ["untrusted-context"]})
    with pytest.raises(MCPAssertionError):
        assert_untrusted_context_quarantined({"text": "hello"})
    assert_context_evicted_on_complete({"status": "done"})
    with pytest.raises(MCPAssertionError, match="retained"):
        assert_context_evicted_on_complete({"context": {"x": 1}})
    sess = SimpleNamespace(context={"a": 1})
    with pytest.raises(MCPAssertionError):
        assert_context_evicted_on_complete(sess)


@pytest.mark.asyncio
async def test_suite_d_cross_tenant() -> None:
    s = MagicMock()
    s.call_tool = AsyncMock(return_value=SimpleNamespace(isError=True, content=[]))
    await assert_cross_tenant_read_denied(s, resource_uri="x", tool_name="read", arguments={})
    s.call_tool = AsyncMock(return_value=SimpleNamespace(isError=False, content=[]))
    with pytest.raises(MCPAssertionError):
        await assert_cross_tenant_read_denied(s, resource_uri="x", tool_name="read")
    s.read_resource = AsyncMock(
        return_value=SimpleNamespace(isError=False, contents=[{"text": "peer"}])
    )
    with pytest.raises(MCPAssertionError, match="contents"):
        await assert_cross_tenant_read_denied(s, resource_uri="res://other")
    s.read_resource = AsyncMock(return_value={"isError": True})
    await assert_cross_tenant_read_denied(s, resource_uri="res://other")
    s.read_resource = AsyncMock(return_value={"message": "denied forbidden"})
    await assert_cross_tenant_read_denied(s, resource_uri="res://other")
    s.read_resource = AsyncMock(return_value={"ok": True})
    with pytest.raises(MCPAssertionError):
        await assert_cross_tenant_read_denied(s, resource_uri="res://other")


def test_attestation_and_capacity_media() -> None:
    assert_unattested_denied_when_required(
        attestation_required=True, server_attested=False, admitted=False
    )
    with pytest.raises(MCPAssertionError):
        assert_unattested_server_denied(
            attestation_required=True, server_attested=False, admitted=True
        )
    assert_unattested_allowed_when_not_required(
        attestation_required=False, server_attested=False, admitted=True
    )
    with pytest.raises(MCPAssertionError):
        assert_unattested_allowed_when_not_required(
            attestation_required=False, server_attested=False, admitted=False
        )
    assert_envelope_verified(envelope_valid=True, accepted=True)
    with pytest.raises(MCPAssertionError):
        assert_envelope_verified(envelope_valid=False, accepted=True)
    with pytest.raises(MCPAssertionError):
        assert_envelope_verified(envelope_valid=True, accepted=False)
    assert_tampered_request_rejected(tampered=True, rejected=True)
    with pytest.raises(MCPAssertionError):
        assert_tampered_request_rejected(tampered=True, rejected=False)
    assert_unauthorized_sampling_dropped(sampling_authorized=False, sampling_delivered=False)
    with pytest.raises(MCPAssertionError):
        assert_unauthorized_sampling_dropped(sampling_authorized=False, sampling_delivered=True)
    assert_tool_allowlist_deny_by_default(
        tool_name="echo", allowlist=["echo"], allowed=True
    )
    with pytest.raises(MCPAssertionError):
        assert_tool_allowlist_deny_by_default(
            tool_name="shell", allowlist=["echo"], allowed=True
        )
    with pytest.raises(MCPAssertionError):
        assert_tool_allowlist_deny_by_default(
            tool_name="echo", allowlist=["echo"], allowed=False
        )
    d = evaluate_attestation_decision(
        {"attestation_required": True, "server_attested": True, "envelope_valid": True}
    )
    assert d["admitted"] is True
    assert_capacity_enforced(
        sink="egress", bytes_attempted=10, budget_bytes=100, admitted_bytes=10
    )
    with pytest.raises(MCPAssertionError):
        assert_capacity_enforced(
            sink="egress", bytes_attempted=10, budget_bytes=100, admitted_bytes=10, denied=True
        )
    with pytest.raises(MCPAssertionError):
        assert_capacity_enforced(
            sink="egress", bytes_attempted=10, budget_bytes=5, admitted_bytes=10
        )
    with pytest.raises(MCPAssertionError):
        assert_capacity_enforced(
            sink="egress",
            bytes_attempted=10,
            budget_bytes=5,
            admitted_bytes=5,
            denied=False,
        )
    assert_capacity_enforced(
        sink="egress", bytes_attempted=10, budget_bytes=5, admitted_bytes=5, denied=True
    )
    with pytest.raises(MCPAssertionError):
        assert_capacity_enforced(
            sink="egress", bytes_attempted=1, budget_bytes=5, admitted_bytes=9
        )
    img = mark_unsigned_suspect_fixture(b"PNG")
    assert_unsigned_media_suspect(img)
    with pytest.raises(MCPAssertionError):
        assert_unsigned_media_suspect(b"")
    with pytest.raises(MCPAssertionError):
        assert_unsigned_media_suspect(b"plain")
    # high lsb entropy path
    alt = bytes([i % 2 for i in range(64)])
    assert_unsigned_media_suspect(alt)
    signed = sign_media_fixture(b"IMG", "key")
    assert_signed_media_exempt(signed, "key")
    with pytest.raises(MCPAssertionError):
        assert_signed_media_exempt(b"nosig", "key")
    with pytest.raises(MCPAssertionError):
        assert_signed_media_exempt(b"IMG\n--SIG--\nbad", "key")


def test_authz_hooks_schema_endpoint_evidence(tmp_path: Path) -> None:
    assert_authorization_not_exposure(
        tool_visible=True, principal_authorized=True, call_allowed=True
    )
    with pytest.raises(MCPAssertionError):
        assert_authorization_not_exposure(
            tool_visible=True, principal_authorized=False, call_allowed=True
        )
    assert_token_audience_validated(
        token_audience="a", resource_audience="a", accepted=True
    )
    with pytest.raises(MCPAssertionError):
        assert_token_audience_validated(
            token_audience="a", resource_audience="b", accepted=True
        )
    with pytest.raises(MCPAssertionError):
        assert_token_audience_validated(
            token_audience="a", resource_audience="a", accepted=False
        )
    assert_no_token_passthrough(inbound_token="t", outbound_token="other")
    with pytest.raises(MCPAssertionError):
        assert_no_token_passthrough(inbound_token="t", outbound_token="t")
    assert_over_privileged_enumeration_denied(
        enumerated_tools=["a"], allowed_tools=["a"]
    )
    with pytest.raises(MCPAssertionError):
        assert_over_privileged_enumeration_denied(
            enumerated_tools=["a", "b"], allowed_tools=["a"]
        )
    assert_scope_bounded_by_owner(owner_permissions=["r"], scope_permissions=["r"])
    with pytest.raises(MCPAssertionError):
        assert_scope_bounded_by_owner(owner_permissions=["r"], scope_permissions=["r", "w"])
    assert_scope_denies_out_of_scope_server(
        scope_server="a", request_server="b", allowed=False
    )
    with pytest.raises(MCPAssertionError):
        assert_scope_denies_out_of_scope_server(
            scope_server="a", request_server="b", allowed=True
        )
    assert_scope_expires(expires_at="2020-01-01T00:00:00Z", now="2021-01-01T00:00:00Z", accepted=False)
    with pytest.raises(MCPAssertionError):
        assert_scope_expires(
            expires_at="2020-01-01T00:00:00Z", now="2021-01-01T00:00:00Z", accepted=True
        )
    assert_scope_audience_bound(
        token_resource="r1", request_resource="r1", accepted=True
    )
    assert_hook_fails_closed_on_no_rule(matched_rule=False, blocked=True)
    with pytest.raises(MCPAssertionError):
        assert_hook_fails_closed_on_no_rule(matched_rule=False, blocked=False)
    assert_hook_fails_closed_on_unknown_server(server_identified=False, blocked=True)
    with pytest.raises(MCPAssertionError):
        assert_hook_fails_closed_on_unknown_server(server_identified=False, blocked=False)
    assert_hook_fails_closed_on_decision_unreachable(
        decision_reachable=False, blocked=True
    )
    with pytest.raises(MCPAssertionError):
        assert_hook_fails_closed_on_decision_unreachable(
            decision_reachable=False, blocked=False
        )
    assert_enforcement_decision_recorded(
        {
            "decision": "deny",
            "device": "d",
            "agent": "a",
            "server": "s",
            "tool": "t",
        }
    )
    with pytest.raises(MCPAssertionError):
        assert_enforcement_decision_recorded({"decision": "deny"})
    with pytest.raises(MCPAssertionError):
        assert_enforcement_decision_recorded(
            {
                "decision": "maybe",
                "device": "d",
                "agent": "a",
                "server": "s",
                "tool": "t",
            }
        )
    findings = evaluate_schema_precondition_rules(
        [
            {"name": "echo", "inputSchema": {"type": "object", "properties": {}}},
            {"name": "bad"},
            {
                "name": "delete_all",
                "inputSchema": {
                    "type": "object",
                    "properties": {"target": {"type": "string"}},
                },
            },
            {
                "name": "ok_del",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "confirm": {"type": "boolean"},
                        "id": {"type": "string", "maxLength": 8},
                    },
                },
            },
            {
                "name": "wide",
                "inputSchema": {
                    "type": "object",
                    "properties": {"q": {"type": "string"}},
                },
            },
        ]
    )
    assert any(f["rule_id"] == "missing-input-schema" for f in findings)
    with pytest.raises(MCPAssertionError):
        assert_schema_preconditions_clean([{"name": "x"}])
    assert_schema_preconditions_clean(
        [
            {
                "name": "echo",
                "inputSchema": {
                    "type": "object",
                    "properties": {"m": {"type": "string", "maxLength": 10}},
                },
            }
        ]
    )
    ndjson = tmp_path / "numbat_findings.ndjson"
    ndjson.write_text(
        json.dumps({"title": "recon", "mitre": ["T1046"], "owasp": ["MCP09"]}) + "\n",
        encoding="utf-8",
    )
    rows = load_numbat_findings(ndjson)
    mapped = assert_endpoint_finding_ingested(rows[0])
    assert mapped["out_of_band"] is True
    assert_endpoint_finding_not_governed(rows[0])
    with pytest.raises(MCPAssertionError):
        assert_endpoint_finding_not_governed({**mapped, "deny_code": "X"})
    with pytest.raises(MCPAssertionError):
        assert_endpoint_finding_not_governed({**mapped, "governed": True})
    oob = out_of_band_coverage_row()
    assert_out_of_band_marked_in_scope_false([oob])
    with pytest.raises(MCPAssertionError):
        assert_out_of_band_marked_in_scope_false([])
    with pytest.raises(MCPAssertionError):
        assert_out_of_band_marked_in_scope_false(
            [CoverageMatrixEntry("oob-execution-path", ("x",), in_scope=True, reason="")]
        )
    with pytest.raises(MCPAssertionError):
        assert_out_of_band_marked_in_scope_false(
            [
                CoverageMatrixEntry(
                    "oob-execution-path", ("x",), in_scope=False, reason=""
                )
            ]
        )
    assert_out_of_band_marked_in_scope_false(
        [{"control_id": "endpoint-numbat", "suites": [], "in_scope": False, "reason": "obs only"}]
    )


def test_evidence_metrics_oscal_reports() -> None:
    r1 = record_from_counts(
        control_id="c1", suite="s1", passed=2, failed=0, owasp_items=["MCP06"], gated=True
    )
    assert r1.outcome == "proven"
    r2 = record_from_counts(
        control_id="c1", suite="night", passed=5, failed=0, gated=False
    )
    assert r2.outcome == "not_proven"
    r3 = record_from_counts(control_id="c2", suite="s1", passed=0, failed=0, gated=True)
    assert r3.outcome == "not_tested"
    r4 = record_from_counts(control_id="c3", suite="s1", passed=0, failed=1, gated=True)
    assert r4.outcome == "not_proven"
    r5 = record_from_counts(
        control_id="c4", suite="s1", passed=0, failed=0, skipped=1, gated=True
    )
    assert r5.outcome == "not_tested"
    eff = control_effectiveness([r1, r2, r4])
    assert eff["controls"]["c1"] == "proven"
    matrix = [
        CoverageMatrixEntry("c1", ("s1",), ("MCP06",), True, ""),
        out_of_band_coverage_row(),
    ]
    cov = owasp_coverage([r1], matrix)
    assert cov["items"]["MCP06"]["proven"] is True
    assert suite_pass_rate([r1, r4])["s1"]["failed"] == 1
    assert adaptive_success_rate(attacks=0, successes=0) == 0.0
    assert detection_rate(attacks=10, detected=5) == 0.5
    assert false_positive_rate(benign=0, flagged=1) == 0.0
    doc = build_assessment_results([r1])
    validate_assessment_results(doc)
    assert "assessment-results" in assessment_results_json([r1])
    with pytest.raises(ValueError):
        validate_assessment_results({})
    with pytest.raises(ValueError):
        validate_assessment_results({"assessment-results": {"uuid": "x"}})
    with pytest.raises(ValueError):
        validate_assessment_results(
            {"assessment-results": {"uuid": "x", "metadata": {}, "results": []}}
        )
    with pytest.raises(ValueError):
        validate_assessment_results(
            {
                "assessment-results": {
                    "uuid": "x",
                    "metadata": {"title": "t"},
                    "results": [{"uuid": "r"}],
                }
            }
        )
    assert records_to_dicts([r1])[0]["control_id"] == "c1"
    assert build_trust_boundary_matrix([r1])
    assert build_launch_gate_readiness(all_gated_green=True)["outcome"].startswith("approve")
    assert "not a compliance" in build_launch_gate_readiness()["disclaimer"]
