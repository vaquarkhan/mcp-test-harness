"""Deterministic structural RCE-precondition rules over tools/list schemas."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from mcp_test_harness.assertions import MCPAssertionError, _result_is_error
from mcp_test_harness.coverage import record_tool_call

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


def find_open_additional_properties(tool: Mapping[str, Any]) -> bool:
    """True when an object input schema with properties does not set additionalProperties false."""
    schema = tool.get("inputSchema") or tool.get("input_schema") or {}
    if not isinstance(schema, Mapping) or schema.get("type") != "object":
        return False
    if not _properties(schema):
        return False
    return schema.get("additionalProperties", None) is not False


def evaluate_schema_bounds(
    tools: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Bounds findings: open additionalProperties and unbounded strings (MCPSTG-INPV-01)."""
    findings: list[dict[str, Any]] = []
    for tool in tools:
        name = str(tool.get("name", ""))
        if find_open_additional_properties(tool):
            findings.append(
                {
                    "rule_id": "additional-properties-open",
                    "mcpstg_ids": ["MCPSTG-INPV-01"],
                    "tool": name,
                    "severity": "medium",
                    "detail": "object inputSchema does not set additionalProperties false",
                }
            )
        for param in find_unbounded_string_params(tool):
            findings.append(
                {
                    "rule_id": "unbounded-string-param",
                    "mcpstg_ids": ["MCPSTG-INPV-01"],
                    "tool": name,
                    "param": param,
                    "severity": "medium",
                    "detail": f"string param {param!r} has no maxLength/enum",
                }
            )
    return findings


def assert_schema_bounds_clean(
    tools: Sequence[Mapping[str, Any]],
    *,
    fail_on: Sequence[str] | None = None,
) -> list[dict[str, Any]]:
    """Fail on schema-bound findings. Opt-in; does not change ``assert_schema_preconditions_clean``."""
    findings = evaluate_schema_bounds(tools)
    watch = set(fail_on or ("additional-properties-open", "unbounded-string-param"))
    bad = [item for item in findings if item["rule_id"] in watch]
    if bad:
        raise MCPAssertionError(
            f"Schema bounds failed ({len(bad)} finding(s)):\n"
            + "\n".join(
                f"  - {item['rule_id']} tool={item.get('tool')} {item.get('detail')}"
                for item in bad[:12]
            )
        )
    return findings


async def assert_schema_bounds_enforced(
    session: Any,
    tool_name: str,
    *,
    argument_name: str = "input",
    max_chars: int = 256,
) -> None:
    """Unknown fields, over-long strings, and wrong types must error (MCPSTG-INPV-01)."""
    probes: tuple[dict[str, Any], ...] = (
        {argument_name: "ok", "_mcp_unknown_field": True},
        {argument_name: "a" * (max_chars + 1)},
        {argument_name: ["not-a-string"]},
    )
    failures: list[str] = []
    for args in probes:
        try:
            result = await session.call_tool(tool_name, args)
        except Exception:
            continue
        if _result_is_error(result):
            continue
        failures.append(f"bounds probe accepted: {sorted(args)!r}")
    record_tool_call(session, tool_name)
    if failures:
        raise MCPAssertionError(
            f"Schema bounds were not enforced ({len(failures)}):\n"
            + "\n".join(f"  - {item}" for item in failures)
        )


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
