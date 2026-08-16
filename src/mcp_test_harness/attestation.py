"""Suite C — attestation / SMCP-class conformance (fixture-driven).

Proves mechanism polarities (advisory vs required), not intent.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from mcp_test_harness.assertions import MCPAssertionError


def assert_unattested_denied_when_required(
    *,
    attestation_required: bool,
    server_attested: bool,
    admitted: bool,
) -> None:
    if attestation_required and not server_attested and admitted:
        raise MCPAssertionError(
            "Unattested server was admitted while attestation is required"
        )


def assert_unattested_allowed_when_not_required(
    *,
    attestation_required: bool,
    server_attested: bool,
    admitted: bool,
) -> None:
    if not attestation_required and not server_attested and not admitted:
        raise MCPAssertionError(
            "Unattested server denied while attestation is advisory/not required"
        )


def assert_unattested_server_denied(
    *,
    attestation_required: bool = True,
    server_attested: bool,
    admitted: bool,
) -> None:
    """Convenience: when required, unattested must be denied."""
    assert_unattested_denied_when_required(
        attestation_required=attestation_required,
        server_attested=server_attested,
        admitted=admitted,
    )


def assert_envelope_verified(*, envelope_valid: bool, accepted: bool) -> None:
    if not envelope_valid and accepted:
        raise MCPAssertionError("Invalid attestation envelope was accepted")
    if envelope_valid and not accepted:
        raise MCPAssertionError("Valid attestation envelope was rejected")


def assert_tampered_request_rejected(*, tampered: bool, rejected: bool) -> None:
    if tampered and not rejected:
        raise MCPAssertionError("Tampered request was not rejected")


def assert_unauthorized_sampling_dropped(
    *,
    sampling_authorized: bool,
    sampling_delivered: bool,
) -> None:
    if not sampling_authorized and sampling_delivered:
        raise MCPAssertionError("Unauthorized sampling was delivered to the model/tool")


def assert_tool_allowlist_deny_by_default(
    *,
    tool_name: str,
    allowlist: Sequence[str],
    allowed: bool,
) -> None:
    listed = tool_name in set(allowlist)
    if not listed and allowed:
        raise MCPAssertionError(
            f"Tool {tool_name!r} allowed but not on allowlist (deny-by-default failed)"
        )
    if listed and not allowed:
        raise MCPAssertionError(
            f"Allowlisted tool {tool_name!r} was denied unexpectedly"
        )


def evaluate_attestation_decision(policy: Mapping[str, Any]) -> dict[str, bool]:
    """Pure helper for fixtures: derive booleans from a policy dict."""
    required = bool(policy.get("attestation_required", False))
    attested = bool(policy.get("server_attested", False))
    envelope_valid = bool(policy.get("envelope_valid", attested))
    tampered = bool(policy.get("tampered", False))
    admitted = (attested and envelope_valid and not tampered) or (
        not required and not tampered
    )
    return {
        "attestation_required": required,
        "server_attested": attested,
        "envelope_valid": envelope_valid,
        "tampered": tampered,
        "admitted": admitted,
        "rejected": not admitted or tampered,
    }
