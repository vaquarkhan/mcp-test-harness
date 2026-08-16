"""OSCAL assessment-results export from ControlEffectivenessRecord[].

Fills assessment-results only — does not author catalog/profile.
"""

from __future__ import annotations

import json
from typing import Any, Sequence

from mcp_test_harness.evidence import ControlEffectivenessRecord


OSCAL_ASSESSMENT_RESULTS_SCHEMA_HINT = (
    "https://pages.nist.gov/OSCAL/concepts/layer/assessment/assessment-results/"
)


def build_assessment_results(
    records: Sequence[ControlEffectivenessRecord],
    *,
    uuid: str = "00000000-0000-4000-8000-000000000001",
    title: str = "MCP Test Harness control effectiveness",
) -> dict[str, Any]:
    """Build a minimal OSCAL assessment-results document."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence")
    observations = []
    findings = []
    for i, r in enumerate(records):
        obs_uuid = f"obs-{i}-{r.control_id}"
        observations.append(
            {
                "uuid": obs_uuid,
                "title": f"Observation for {r.control_id}",
                "description": (
                    f"suite={r.suite} outcome={r.outcome} "
                    f"passed={r.passed} failed={r.failed} skipped={r.skipped}"
                ),
                "methods": ["TEST"],
                "subjects": [{"type": "component", "title": r.control_id}],
                "collected": r.ts or None,
            }
        )
        findings.append(
            {
                "uuid": f"finding-{i}-{r.control_id}",
                "title": f"{r.control_id}: {r.outcome}",
                "description": f"OWASP={list(r.owasp_items)} run_id={r.run_id}",
                "related-observations": [obs_uuid],
                "target": {
                    "type": "objective-id",
                    "target-id": r.control_id,
                    "status": {
                        "state": "satisfied" if r.outcome == "proven" else "not-satisfied"
                    },
                },
            }
        )
    doc = {
        "assessment-results": {
            "uuid": uuid,
            "metadata": {
                "title": title,
                "version": "1.0.0",
                "oscal-version": "1.1.2",
            },
            "results": [
                {
                    "uuid": "result-1",
                    "title": title,
                    "observations": observations,
                    "findings": findings,
                }
            ],
        }
    }
    validate_assessment_results(doc)
    return doc


def validate_assessment_results(doc: dict[str, Any]) -> None:
    """Lightweight structural validation — fail generation on bad shape."""
    root = doc.get("assessment-results")
    if not isinstance(root, dict):
        raise ValueError("OSCAL export missing assessment-results object")
    if "uuid" not in root or "metadata" not in root or "results" not in root:
        raise ValueError("OSCAL assessment-results missing uuid/metadata/results")
    meta = root["metadata"]
    if not isinstance(meta, dict) or "title" not in meta:
        raise ValueError("OSCAL metadata.title required")
    results = root["results"]
    if not isinstance(results, list) or not results:
        raise ValueError("OSCAL results must be a non-empty list")
    for res in results:
        if "observations" not in res or "findings" not in res:
            raise ValueError("OSCAL result requires observations and findings")


def assessment_results_json(
    records: Sequence[ControlEffectivenessRecord],
    **kwargs: Any,
) -> str:
    return json.dumps(build_assessment_results(records, **kwargs), indent=2, sort_keys=True)
