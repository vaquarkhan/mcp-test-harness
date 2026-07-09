"""Load the bundled resiliency experiment catalog."""

from __future__ import annotations

from importlib import resources
from pathlib import Path
from typing import Any

import yaml

from mcp_test_harness.experiments.models import (
    ExperimentCatalog,
    ExperimentFault,
    ExperimentStopCondition,
    ExperimentSuite,
    ExperimentTemplate,
)


def _parse_fault(raw: dict[str, Any] | None) -> ExperimentFault:
    data = raw or {}
    faults = data.get("chaos_faults") or []
    return ExperimentFault(
        type=str(data.get("type", "none")),
        chaos_faults=[str(f) for f in faults],
    )


def _parse_stop(raw: dict[str, Any] | None) -> ExperimentStopCondition:
    data = raw or {}
    abort = data.get("abort_if") or []
    return ExperimentStopCondition(abort_if=tuple(str(a) for a in abort))


def _parse_experiment(exp_id: str, raw: dict[str, Any]) -> ExperimentTemplate:
    status = str(raw.get("status", "planned"))
    if status not in ("ready", "planned"):
        status = "planned"
    target = raw.get("target") or {}
    tool = target.get("tool") if isinstance(target, dict) else None
    return ExperimentTemplate(
        id=exp_id,
        title=str(raw.get("title", exp_id)),
        hypothesis=str(raw.get("hypothesis", "")),
        status=status,  # type: ignore[arg-type]
        assertion=str(raw.get("assertion", "")),
        fault=_parse_fault(raw.get("fault")),
        target_tool=str(tool) if tool else None,
        stop_condition=_parse_stop(raw.get("stop_condition")),
        timeout=raw.get("timeout"),
        raw=dict(raw),
    )


def load_catalog(path: Path | None = None) -> ExperimentCatalog:
    """Load catalog YAML from *path* or the bundled default."""
    if path is None:
        text = resources.files("mcp_test_harness.experiments").joinpath("catalog.yaml").read_text(
            encoding="utf-8",
        )
        data = yaml.safe_load(text) or {}
    else:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    version = int(data.get("version", 1))
    experiments_raw: dict[str, Any] = data.get("experiments") or {}
    experiments = {
        exp_id: _parse_experiment(exp_id, body)
        for exp_id, body in experiments_raw.items()
        if isinstance(body, dict)
    }

    suites: dict[str, ExperimentSuite] = {}
    for name, body in (data.get("suites") or {}).items():
        if not isinstance(body, dict):
            continue
        members_raw = body.get("members") or []
        if members_raw == "all" or members_raw == ["all"]:
            members = tuple(sorted(experiments.keys()))
        else:
            members = tuple(str(m) for m in members_raw)
        suites[str(name)] = ExperimentSuite(
            name=str(name),
            description=str(body.get("description", "")),
            members=members,
        )

    return ExperimentCatalog(version=version, experiments=experiments, suites=suites)


def list_experiment_ids(catalog: ExperimentCatalog | None = None) -> list[str]:
    """Return sorted experiment ids."""
    cat = catalog or load_catalog()
    return sorted(cat.experiments.keys())


def get_experiment(exp_id: str, catalog: ExperimentCatalog | None = None) -> ExperimentTemplate:
    """Return one experiment or raise KeyError."""
    cat = catalog or load_catalog()
    if exp_id not in cat.experiments:
        raise KeyError(f"Unknown experiment: {exp_id}")
    return cat.experiments[exp_id]


def resolve_suite_members(
    suite_name: str,
    catalog: ExperimentCatalog | None = None,
) -> list[str]:
    """Return experiment ids for a named suite."""
    cat = catalog or load_catalog()
    if suite_name not in cat.suites:
        raise KeyError(f"Unknown suite: {suite_name}")
    return list(cat.suites[suite_name].members)
