"""Static hygiene checks for MCP tool and prompt definitions.

Detects hidden Unicode, instruction-override text in descriptions, and
annotation lies (a destructive tool marked read-only). This is a CI gate
over ``tools/list`` / ``prompts/get`` payloads. It does not generate
payloads or call a model.
"""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from mcp_test_harness.agents_md_scan import scan_text_for_hidden_unicode
from mcp_test_harness.assertions import MCPAssertionError
from mcp_test_harness.schema_rules import DESTRUCTIVE_NAME_HINTS

# Phrases that mean the definition is trying to steer the model, not describe the tool.
_OVERRIDE = re.compile(
    r"ignore (?:all |any )?(?:previous|prior|above) instructions"
    r"|disregard (?:the )?(?:user|developer|system)"
    r"|do not tell the user"
    r"|you are now"
    r"|exfiltrat"
    r"|override (?:the )?system prompt",
    re.IGNORECASE,
)


def _annotations(tool: Mapping[str, Any]) -> Mapping[str, Any]:
    raw = tool.get("annotations")
    return raw if isinstance(raw, Mapping) else {}


def _texts(item: Mapping[str, Any]) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for field in ("name", "description"):
        value = item.get(field)
        if isinstance(value, str) and value:
            found.append((field, value))
    return found


def evaluate_tool_definition_hygiene(
    tools: Sequence[Mapping[str, Any]],
    prompts: Sequence[Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Return hygiene findings. Empty means the advertised surface looks clean."""
    findings: list[dict[str, Any]] = []
    for tool in tools:
        name = str(tool.get("name") or "")
        for field, text in _texts(tool):
            for hit in scan_text_for_hidden_unicode(text, path=f"tool:{name}:{field}"):
                findings.append(
                    {
                        "rule_id": "hidden-unicode-definition",
                        "mcpstg_ids": ["MCPSTG-PRMT-04", "MCPSTG-TOOL-01"],
                        "kind": "tool",
                        "name": name,
                        "field": field,
                        "severity": hit.severity,
                        "detail": f"{hit.band} at {hit.codepoint}",
                    }
                )
            if field == "description" and _OVERRIDE.search(text):
                findings.append(
                    {
                        "rule_id": "instruction-override",
                        "mcpstg_ids": ["MCPSTG-TOOL-01", "MCPSTG-PRMT-03"],
                        "kind": "tool",
                        "name": name,
                        "field": field,
                        "severity": "high",
                        "detail": "description contains instruction-override text",
                    }
                )
        lowered = name.lower()
        if any(hint in lowered for hint in DESTRUCTIVE_NAME_HINTS):
            ann = _annotations(tool)
            if ann.get("readOnlyHint") is True:
                findings.append(
                    {
                        "rule_id": "readonly-hint-on-destructive",
                        "mcpstg_ids": ["MCPSTG-TOOL-04"],
                        "kind": "tool",
                        "name": name,
                        "severity": "high",
                        "detail": "destructive tool sets annotations.readOnlyHint true",
                    }
                )
            if ann.get("destructiveHint") is False:
                findings.append(
                    {
                        "rule_id": "destructive-hint-false",
                        "mcpstg_ids": ["MCPSTG-TOOL-04"],
                        "kind": "tool",
                        "name": name,
                        "severity": "high",
                        "detail": "destructive tool sets annotations.destructiveHint false",
                    }
                )
    for prompt in prompts or ():
        pname = str(prompt.get("name") or "")
        for field, text in _texts(prompt):
            for hit in scan_text_for_hidden_unicode(text, path=f"prompt:{pname}:{field}"):
                findings.append(
                    {
                        "rule_id": "hidden-unicode-definition",
                        "mcpstg_ids": ["MCPSTG-PRMT-04", "MCPSTG-PRMT-05"],
                        "kind": "prompt",
                        "name": pname,
                        "field": field,
                        "severity": hit.severity,
                        "detail": f"{hit.band} at {hit.codepoint}",
                    }
                )
            if field == "description" and _OVERRIDE.search(text):
                findings.append(
                    {
                        "rule_id": "instruction-override",
                        "mcpstg_ids": ["MCPSTG-PRMT-03", "MCPSTG-PRMT-05"],
                        "kind": "prompt",
                        "name": pname,
                        "field": field,
                        "severity": "high",
                        "detail": "prompt description contains instruction-override text",
                    }
                )
    return findings


def assert_tool_definitions_clean(
    tools: Sequence[Mapping[str, Any]],
    prompts: Sequence[Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Fail when tool or prompt definitions carry hygiene findings."""
    findings = evaluate_tool_definition_hygiene(tools, prompts)
    if findings:
        raise MCPAssertionError(
            f"Tool definition hygiene failed ({len(findings)} finding(s)):\n"
            + "\n".join(
                f"  - {f['rule_id']} {f.get('kind')}={f.get('name')} {f.get('detail')}"
                for f in findings[:12]
            )
        )
    return findings
