"""MCP Test Harness -- a pytest-style testing framework for MCP servers."""

from __future__ import annotations

__version__ = "5.2.0"

__all__ = [
    "__version__",
    "MCPAssertionError",
    "assert_agents_md_clean",
    "assert_audit_chain_intact",
    "assert_authorization_boundary",
    "assert_authorization_not_exposure",
    "assert_benchmark_egress_denied",
    "assert_capabilities",
    "assert_capacity_enforced",
    "assert_command_injection_blocked",
    "assert_context_evicted_on_complete",
    "assert_control_engages_under_load",
    "assert_covert_channel_neutralized",
    "assert_cross_tenant_read_denied",
    "assert_degrades_gracefully",
    "assert_detection_rate",
    "assert_dns_egress_denied",
    "assert_egress_allowed",
    "assert_egress_quarantined",
    "assert_endpoint_finding_ingested",
    "assert_endpoint_finding_not_governed",
    "assert_envelope_verified",
    "assert_fairness_under_load",
    "assert_false_positive_rate",
    "assert_general_exec_tools_absent",
    "assert_injection_blocked",
    "assert_invalid_tool",
    "assert_latency",
    "assert_latency_slo_until_shed",
    "assert_latency_within_baseline",
    "assert_load_phases",
    "assert_manifest_hash_matches",
    "assert_manifest_snapshot",
    "assert_memory_write_guarded",
    "assert_no_fail_open_under_load",
    "assert_no_secret_leak",
    "assert_no_token_passthrough",
    "assert_out_of_band_marked_in_scope_false",
    "assert_path_symlink_escape_blocked",
    "assert_path_traversal_blocked",
    "assert_prompt",
    "assert_protocol_version",
    "assert_reconnects",
    "assert_resource_list",
    "assert_resource_read",
    "assert_schema_preconditions_clean",
    "assert_signed_media_exempt",
    "assert_snapshot",
    "assert_stateless_throughput",
    "assert_survives_crash",
    "assert_tampered_request_rejected",
    "assert_throughput",
    "assert_tool_allowlist_deny_by_default",
    "assert_tool_call",
    "assert_tool_call_validates_input",
    "assert_tool_denied",
    "assert_tool_idempotent",
    "assert_tool_list",
    "assert_tool_rejects",
    "assert_tool_schema",
    "assert_transport_binding_hardened",
    "assert_unattested_server_denied",
    "assert_untrusted_context_quarantined",
    "assert_unsigned_media_suspect",
    "assert_url_exfil_bounded",
    "build_assessment_results",
    "capture_server_manifest",
    "coverage_to_dict",
    "marker",
    "run_adaptive_trend",
    "run_security_payload_pack",
    "save_baseline",
    "scan_project_agent_rules",
    "skip",
]

from mcp_test_harness.assertions import (
    MCPAssertionError,
    assert_capabilities,
    assert_authorization_boundary,
    assert_invalid_tool,
    assert_latency,
    assert_throughput,
    assert_load_phases,
    assert_stateless_throughput,
    assert_prompt,
    assert_protocol_version,
    assert_resource_list,
    assert_resource_read,
    assert_snapshot,
    assert_tool_call,
    assert_tool_call_validates_input,
    assert_tool_denied,
    assert_tool_idempotent,
    assert_tool_list,
    assert_tool_rejects,
    assert_tool_schema,
)
from mcp_test_harness.discovery import marker, skip
from mcp_test_harness.baselines import assert_latency_within_baseline, save_baseline
from mcp_test_harness.coverage import coverage_to_dict
from mcp_test_harness.agents_md_scan import (
    assert_agents_md_clean,
    scan_project_agent_rules,
)
from mcp_test_harness.adaptive import (
    assert_detection_rate,
    assert_false_positive_rate,
    run_adaptive_trend,
)
from mcp_test_harness.attestation import (
    assert_envelope_verified,
    assert_tampered_request_rejected,
    assert_tool_allowlist_deny_by_default,
    assert_unattested_server_denied,
)
from mcp_test_harness.audit_chain import assert_audit_chain_intact
from mcp_test_harness.authz_conformance import (
    assert_authorization_not_exposure,
    assert_no_token_passthrough,
)
from mcp_test_harness.endpoint_evidence import (
    assert_endpoint_finding_ingested,
    assert_endpoint_finding_not_governed,
    assert_out_of_band_marked_in_scope_false,
)
from mcp_test_harness.incident_conformance import (
    assert_benchmark_egress_denied,
    assert_command_injection_blocked,
    assert_dns_egress_denied,
    assert_manifest_hash_matches,
    assert_memory_write_guarded,
    assert_path_symlink_escape_blocked,
    assert_transport_binding_hardened,
    assert_url_exfil_bounded,
)
from mcp_test_harness.load_resilience import (
    assert_control_engages_under_load,
    assert_fairness_under_load,
    assert_latency_slo_until_shed,
    assert_no_fail_open_under_load,
)
from mcp_test_harness.manifest_gate import assert_manifest_snapshot, capture_server_manifest
from mcp_test_harness.oscal import build_assessment_results
from mcp_test_harness.resiliency import (
    assert_degrades_gracefully,
    assert_reconnects,
    assert_survives_crash,
)
from mcp_test_harness.schema_rules import assert_schema_preconditions_clean
from mcp_test_harness.security_payloads import (
    assert_covert_channel_neutralized,
    assert_egress_allowed,
    assert_egress_quarantined,
    assert_general_exec_tools_absent,
    assert_injection_blocked,
    assert_no_secret_leak,
    assert_path_traversal_blocked,
    run_security_payload_pack,
)
from mcp_test_harness.suite_b_capacity import (
    assert_capacity_enforced,
    assert_signed_media_exempt,
    assert_unsigned_media_suspect,
)
from mcp_test_harness.suite_d import (
    assert_context_evicted_on_complete,
    assert_cross_tenant_read_denied,
    assert_untrusted_context_quarantined,
)
