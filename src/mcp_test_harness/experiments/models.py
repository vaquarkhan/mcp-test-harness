"""Data models for the resiliency experiment catalog."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

ExperimentStatus = Literal["ready", "planned"]


@dataclass(frozen=True)
class ExperimentFault:
    """Fault configuration for an experiment template."""

    type: str = "none"
    chaos_faults: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ExperimentStopCondition:
    """Guardrail triggers that abort an experiment run."""

    abort_if: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExperimentTemplate:
    """A single catalog experiment definition."""

    id: str
    title: str
    hypothesis: str
    status: ExperimentStatus
    assertion: str = ""
    fault: ExperimentFault = field(default_factory=ExperimentFault)
    target_tool: str | None = None
    stop_condition: ExperimentStopCondition = field(default_factory=ExperimentStopCondition)
    timeout: float | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExperimentSuite:
    """Named group of experiment ids."""

    name: str
    description: str
    members: tuple[str, ...]


@dataclass
class ExperimentCatalog:
    """Loaded experiment catalog."""

    version: int
    experiments: dict[str, ExperimentTemplate]
    suites: dict[str, ExperimentSuite]
