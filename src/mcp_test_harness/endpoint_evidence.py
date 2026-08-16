"""Endpoint-layer (Numbat-class) evidence ingestion contract — fixtures only.

Green means mapping/contract is honest (out_of_band, never governed/proven),
not that Numbat detected anything.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from mcp_test_harness.assertions import MCPAssertionError
from mcp_test_harness.evidence import CoverageMatrixEntry


def load_numbat_findings(path: str | Path) -> list[dict[str, Any]]:
    text = Path(path).read_text(encoding="utf-8")
    rows: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def map_numbat_finding(record: Mapping[str, Any]) -> dict[str, Any]:
    if "mitre" in record:
        mitre = record.get("mitre")
    else:
        mitre = record.get("mitre_attack") or []
    return {
        "source": "numbat",
        "out_of_band": True,
        "in_scope": False,
        "mitre": mitre,
        "owasp": record.get("owasp") or [],
        "title": record.get("title") or record.get("rule") or "numbat-finding",
        "raw": dict(record),
    }


def assert_endpoint_finding_ingested(record: Mapping[str, Any]) -> dict[str, Any]:
    mapped = map_numbat_finding(record)
    if mapped["source"] != "numbat":
        raise MCPAssertionError("endpoint finding source must be numbat")
    if not mapped["out_of_band"]:
        raise MCPAssertionError("endpoint finding must be out_of_band=true")
    if mapped.get("mitre") is None:
        raise MCPAssertionError("endpoint finding lost MITRE metadata")
    return mapped


def assert_endpoint_finding_not_governed(record: Mapping[str, Any]) -> None:
    mapped = map_numbat_finding(record) if "source" not in record else dict(record)
    forbidden_keys = (
        "deny_code",
        "governed_decision",
        "bastion_deny",
        "proven_control",
        "receipt",
    )
    for key in forbidden_keys:
        if mapped.get(key):
            raise MCPAssertionError(
                f"Endpoint finding incorrectly treated as governed ({key} present)"
            )
    if mapped.get("source") == "numbat" and mapped.get("governed") is True:
        raise MCPAssertionError("Numbat finding marked governed=true")


def assert_out_of_band_marked_in_scope_false(
    matrix: Sequence[CoverageMatrixEntry] | Sequence[Mapping[str, Any]],
) -> None:
    rows = []
    for e in matrix:
        if isinstance(e, CoverageMatrixEntry):
            rows.append(e)
        else:
            rows.append(
                CoverageMatrixEntry(
                    control_id=str(e.get("control_id", "")),
                    suites=tuple(e.get("suites") or ()),
                    owasp_items=tuple(e.get("owasp_items") or ()),
                    in_scope=bool(e.get("in_scope", True)),
                    reason=str(e.get("reason") or ""),
                )
            )
    hits = [
        r
        for r in rows
        if r.control_id in {"oob-execution-path", "endpoint-numbat", "out-of-band"}
        or "out_of_band" in r.control_id
        or "oob" in r.control_id
    ]
    if not hits:
        raise MCPAssertionError(
            "Coverage matrix missing out-of-band / endpoint row (in_scope=false expected)"
        )
    for r in hits:
        if r.in_scope:
            raise MCPAssertionError(
                f"Out-of-band row {r.control_id!r} must be in_scope=false"
            )
        if not r.reason:
            raise MCPAssertionError(
                f"Out-of-band row {r.control_id!r} requires a reason"
            )
