"""Confused-deputy, scoped-credential, and pre-tool-hook conformance (fixtures)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from mcp_test_harness.assertions import MCPAssertionError


def assert_authorization_not_exposure(
    *,
    tool_visible: bool,
    principal_authorized: bool,
    call_allowed: bool,
) -> None:
    if tool_visible and not principal_authorized and call_allowed:
        raise MCPAssertionError(
            "Confused deputy: visible tool allowed for unauthorized principal"
        )


def assert_token_audience_validated(
    *,
    token_audience: str,
    resource_audience: str,
    accepted: bool,
) -> None:
    match = token_audience == resource_audience
    if not match and accepted:
        raise MCPAssertionError(
            f"Token audience mismatch accepted ({token_audience!r} vs {resource_audience!r})"
        )
    if match and not accepted:
        raise MCPAssertionError("Matching token audience unexpectedly rejected")


def assert_no_token_passthrough(
    *,
    inbound_token: str,
    outbound_token: str | None,
) -> None:
    if outbound_token and outbound_token == inbound_token:
        raise MCPAssertionError("Token passthrough detected (inbound token forwarded)")


def assert_over_privileged_enumeration_denied(
    *,
    enumerated_tools: Sequence[str],
    allowed_tools: Sequence[str],
) -> None:
    allow = set(allowed_tools)
    extra = [t for t in enumerated_tools if t not in allow]
    if extra:
        raise MCPAssertionError(
            "Over-privileged enumeration leaked tools: " + ", ".join(extra)
        )


def assert_scope_bounded_by_owner(
    *,
    owner_permissions: Sequence[str],
    scope_permissions: Sequence[str],
) -> None:
    owner = set(owner_permissions)
    excess = [p for p in scope_permissions if p not in owner]
    if excess:
        raise MCPAssertionError(
            "Scope grants more than owner holds: " + ", ".join(excess)
        )


def assert_scope_denies_out_of_scope_server(
    *,
    scope_server: str,
    request_server: str,
    allowed: bool,
) -> None:
    if scope_server != request_server and allowed:
        raise MCPAssertionError(
            f"Scope for server {scope_server!r} allowed call to {request_server!r}"
        )


def assert_scope_expires(*, expires_at: str, now: str | None = None, accepted: bool) -> None:
    now_s = now or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if expires_at <= now_s and accepted:
        raise MCPAssertionError(f"Expired scope accepted (expires_at={expires_at})")


def assert_scope_audience_bound(
    *,
    token_resource: str,
    request_resource: str,
    accepted: bool,
) -> None:
    assert_token_audience_validated(
        token_audience=token_resource,
        resource_audience=request_resource,
        accepted=accepted,
    )


def assert_hook_fails_closed_on_no_rule(*, matched_rule: bool, blocked: bool) -> None:
    if not matched_rule and not blocked:
        raise MCPAssertionError("Pre-tool hook fail-open: no rule matched but call allowed")


def assert_hook_fails_closed_on_unknown_server(
    *,
    server_identified: bool,
    blocked: bool,
) -> None:
    if not server_identified and not blocked:
        raise MCPAssertionError("Pre-tool hook fail-open: unknown server allowed")


def assert_hook_fails_closed_on_decision_unreachable(
    *,
    decision_reachable: bool,
    blocked: bool,
) -> None:
    if not decision_reachable and not blocked:
        raise MCPAssertionError(
            "Pre-tool hook fail-open: decision service unreachable but call allowed"
        )


def assert_enforcement_decision_recorded(record: Mapping[str, Any]) -> None:
    required = ("decision", "device", "agent", "server", "tool")
    missing = [k for k in required if not record.get(k)]
    if missing:
        raise MCPAssertionError(
            "Enforcement decision record missing fields: " + ", ".join(missing)
        )
    if str(record["decision"]).lower() not in {"allow", "deny", "blocked", "allowed"}:
        raise MCPAssertionError(f"Invalid decision value: {record['decision']!r}")
