"""Deterministic structural RCE-precondition rules over tools/list schemas."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from mcp_test_harness.assertions import MCPAssertionError

DESTRUCTIVE_NAME_HINTS: tuple[str, ...] = (
    "delete",
    "remove",
    "drop",
    "destroy",
    "exec",
    "shell",
    "write_file",
    "rm",
)


def _properties(schema: Mapping[str, Any] | None) -> dict[str, Any]:
    if not schema:
        return {}
    props = schema.get("properties")
    return props if isinstance(props, dict) else {}


def find_unbounded_string_params(tool: Mapping[str, Any]) -> list[str]:
    schema = tool.get("inputSchema") or tool.get("input_schema") or {}
    if not isinstance(schema, Mapping):
        return []
    hits: list[str] = []
    for name, prop in _properties(schema).items():
        if not isinstance(prop, Mapping):
            continue
        if prop.get("type") == "string" and "maxLength" not in prop and "enum" not in prop:
            hits.append(str(name))
    return hits


def missing_input_schema(tool: Mapping[str, Any]) -> bool:
    schema = tool.get("inputSchema") or tool.get("input_schema")
    return not isinstance(schema, Mapping) or not schema


def destructive_without_constraints(tool: Mapping[str, Any]) -> bool:
    name = str(tool.get("name", "")).lower()
    if not any(h in name for h in DESTRUCTIVE_NAME_HINTS):
        return False
    schema = tool.get("inputSchema") or tool.get("input_schema") or {}
    if not isinstance(schema, Mapping):
        return True
    props = _properties(schema)
    if not props:
        return True
    # Require at least one constrained argument or confirmation field
    for prop in props.values():
        if not isinstance(prop, Mapping):
            continue
        if "enum" in prop or "const" in prop or "maxLength" in prop:
            return False
        if str(prop.get("title", "")).lower() in {"confirm", "approval"}:
            return False
    return "confirm" not in {k.lower() for k in props} and "approval" not in {
        k.lower() for k in props
    }


def evaluate_schema_precondition_rules(
    tools: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for tool in tools:
        name = str(tool.get("name", ""))
        if missing_input_schema(tool):
            findings.append(
                {
                    "rule_id": "missing-input-schema",
                    "tool": name,
                    "severity": "high",
                    "detail": "tool declares no inputSchema",
                }
            )
        for param in find_unbounded_string_params(tool):
            findings.append(
                {
                    "rule_id": "unbounded-string-param",
                    "tool": name,
                    "param": param,
                    "severity": "medium",
                    "detail": f"string param {param!r} has no maxLength/enum",
                }
            )
        if destructive_without_constraints(tool):
            findings.append(
                {
                    "rule_id": "destructive-without-constraints",
                    "tool": name,
                    "severity": "high",
                    "detail": "destructive tool lacks constrained/confirm args",
                }
            )
    return findings


def assert_schema_preconditions_clean(
    tools: Sequence[Mapping[str, Any]],
    *,
    fail_on: Sequence[str] | None = None,
) -> list[dict[str, Any]]:
    """Fail when structural precondition findings exist (risk signals, not exploits)."""
    findings = evaluate_schema_precondition_rules(tools)
    watch = set(fail_on or ("missing-input-schema", "destructive-without-constraints", "unbounded-string-param"))
    bad = [f for f in findings if f["rule_id"] in watch]
    if bad:
        raise MCPAssertionError(
            f"Schema RCE-precondition rules failed ({len(bad)} finding(s)):\n"
            + "\n".join(
                f"  - {f['rule_id']} tool={f.get('tool')} {f.get('detail')}"
                for f in bad[:12]
            )
        )
    return findings
