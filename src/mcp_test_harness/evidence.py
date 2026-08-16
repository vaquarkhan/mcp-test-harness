"""Assurance evidence dataclasses (harness half of governance/compliance).

``proven`` only from gated deterministic suites — nightly never flips proven.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, Literal, Sequence

Outcome = Literal["proven", "not_proven", "not_tested"]


@dataclass(frozen=True)
class ControlEffectivenessRecord:
    control_id: str
    suite: str
    outcome: Outcome
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    owasp_items: tuple[str, ...] = ()
    run_id: str = ""
    ts: str = ""
    catalog_version: str = "1"


@dataclass(frozen=True)
class CoverageMatrixEntry:
    control_id: str
    suites: tuple[str, ...]
    owasp_items: tuple[str, ...] = ()
    in_scope: bool = True
    reason: str = ""


def make_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def record_from_counts(
    *,
    control_id: str,
    suite: str,
    passed: int,
    failed: int,
    skipped: int = 0,
    owasp_items: Sequence[str] = (),
    run_id: str = "",
    gated: bool = True,
    catalog_version: str = "1",
) -> ControlEffectivenessRecord:
    """Build a record; nightly (gated=False) can never become proven."""
    if not gated:
        outcome: Outcome = "not_proven" if (passed or failed) else "not_tested"
    elif passed + failed + skipped == 0:
        outcome = "not_tested"
    elif failed > 0:
        outcome = "not_proven"
    elif passed > 0:
        outcome = "proven"
    else:
        outcome = "not_tested"
    return ControlEffectivenessRecord(
        control_id=control_id,
        suite=suite,
        outcome=outcome,
        passed=passed,
        failed=failed,
        skipped=skipped,
        owasp_items=tuple(owasp_items),
        run_id=run_id,
        ts=make_timestamp(),
        catalog_version=catalog_version,
    )


def out_of_band_coverage_row() -> CoverageMatrixEntry:
    return CoverageMatrixEntry(
        control_id="oob-execution-path",
        suites=("capability-reduction-config",),
        owasp_items=("MCP09", "ASI10"),
        in_scope=False,
        reason="Direct out-of-band host execution is validated by OS sandbox / "
        "capability-reduction config checks, not MCP server tests",
    )


def records_to_dicts(records: Iterable[ControlEffectivenessRecord]) -> list[dict[str, Any]]:
    return [asdict(r) for r in records]


def matrix_to_dicts(entries: Iterable[CoverageMatrixEntry]) -> list[dict[str, Any]]:
    return [asdict(e) for e in entries]
