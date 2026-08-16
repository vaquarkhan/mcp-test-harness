"""Load / resource-exhaustion resilience assertions (availability as security).

Gate on control engagement and no-fail-open. Absolute RPS/p99 stay reported,
not required here.
"""

from __future__ import annotations

import asyncio
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from mcp_test_harness.assertions import (
    MCPAssertionError,
    _normalize_load_calls,
    _pick_load_call,
    _result_error_text,
    _result_is_error,
)
from mcp_test_harness.coverage import record_tool_call

DENY_CODES: frozenset[str] = frozenset(
    {
        "RATE_LIMITED",
        "CONCURRENCY_LIMIT",
        "LOAD_SHED",
        "CIRCUIT_OPEN",
    }
)

ERROR_KINDS: frozenset[str] = frozenset(
    {"tool_error", "rpc_error", "timeout", "exception", "ok", "deny"}
)


@dataclass
class LoadCallOutcome:
    """One classified call under load."""

    ok: bool
    error_kind: str
    deny_code: str | None = None
    latency_ms: float = 0.0
    tenant: str | None = None


@dataclass
class LoadResilienceReport:
    """Aggregate classification for a load burst/ramp."""

    outcomes: list[LoadCallOutcome] = field(default_factory=list)

    @property
    def deny_counts(self) -> Counter[str]:
        c: Counter[str] = Counter()
        for o in self.outcomes:
            if o.deny_code:
                c[o.deny_code] += 1
        return c

    @property
    def kind_counts(self) -> Counter[str]:
        return Counter(o.error_kind for o in self.outcomes)

    @property
    def admitted(self) -> list[LoadCallOutcome]:
        return [o for o in self.outcomes if o.ok]

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": len(self.outcomes),
            "deny_counts": dict(self.deny_counts),
            "kind_counts": dict(self.kind_counts),
            "admitted": len(self.admitted),
        }


def classify_load_failure(
    *,
    raised: BaseException | None = None,
    result: Any = None,
    timed_out: bool = False,
) -> tuple[str, str | None]:
    """Return ``(error_kind, deny_code|None)``.

    A crashed handler must classify as ``exception``, never a clean deny code.
    """
    if timed_out:
        return "timeout", None
    if raised is not None:
        name = type(raised).__name__.lower()
        msg = str(raised).upper()
        for code in DENY_CODES:
            if code in msg or code.replace("_", "") in msg.replace("_", ""):
                return "deny", code
        if "timeout" in name or "timeout" in msg.lower():
            return "timeout", None
        if "rpc" in name or "jsonrpc" in msg.lower():
            return "rpc_error", None
        return "exception", None
    if result is not None and _result_is_error(result):
        text = _result_error_text(result).upper()
        for code in DENY_CODES:
            if code in text:
                return "deny", code
        # MCP tool error without deny code
        return "tool_error", None
    return "ok", None


async def _run_classified_burst(
    session: Any,
    catalog: list[tuple[str, dict[str, Any], float]],
    *,
    concurrent: int,
    total_calls: int,
    tenant: str | None = None,
) -> LoadResilienceReport:
    report = LoadResilienceReport()
    sem = asyncio.Semaphore(max(1, concurrent))
    lock = asyncio.Lock()

    async def one() -> None:
        tool, args = _pick_load_call(catalog)
        t0 = time.perf_counter()
        raised: BaseException | None = None
        result: Any = None
        timed_out = False
        async with sem:
            try:
                result = await asyncio.wait_for(
                    session.call_tool(tool, args),
                    timeout=30.0,
                )
            except asyncio.TimeoutError:
                timed_out = True
            except Exception as exc:  # noqa: BLE001 — classify all
                raised = exc
        elapsed = (time.perf_counter() - t0) * 1000.0
        kind, deny = classify_load_failure(
            raised=raised, result=result, timed_out=timed_out
        )
        ok = kind == "ok"
        async with lock:
            report.outcomes.append(
                LoadCallOutcome(
                    ok=ok,
                    error_kind=kind,
                    deny_code=deny,
                    latency_ms=elapsed,
                    tenant=tenant,
                )
            )

    await asyncio.gather(*[one() for _ in range(max(1, total_calls))])
    if catalog:
        record_tool_call(session, catalog[0][0])
    return report


async def collect_load_resilience(
    session: Any,
    tool_name: str = "",
    arguments: dict[str, Any] | None = None,
    *,
    calls: Sequence[Mapping[str, Any]] | None = None,
    concurrent: int = 4,
    total_calls: int = 16,
    tenant: str | None = None,
) -> LoadResilienceReport:
    """Run a classified burst and return the report."""
    catalog = _normalize_load_calls(tool_name, arguments, calls)
    return await _run_classified_burst(
        session,
        catalog,
        concurrent=concurrent,
        total_calls=total_calls,
        tenant=tenant,
    )


async def assert_control_engages_under_load(
    session: Any,
    tool_name: str = "",
    arguments: dict[str, Any] | None = None,
    *,
    calls: Sequence[Mapping[str, Any]] | None = None,
    concurrent: int = 8,
    total_calls: int = 32,
    expect_deny_code: str,
) -> LoadResilienceReport:
    """Dominant deny code must be the expected availability control."""
    code = expect_deny_code.upper()
    if code not in DENY_CODES:
        raise ValueError(f"expect_deny_code must be one of {sorted(DENY_CODES)}")
    report = await collect_load_resilience(
        session,
        tool_name,
        arguments,
        calls=calls,
        concurrent=concurrent,
        total_calls=total_calls,
    )
    denies = report.deny_counts
    if not denies:
        # Also fail if dominated by timeout/exception
        kinds = report.kind_counts
        raise MCPAssertionError(
            f"Control did not engage under load (no deny codes); kinds={dict(kinds)}"
        )
    dominant = denies.most_common(1)[0][0]
    if dominant != code:
        raise MCPAssertionError(
            f"Expected dominant deny {code}, got {dominant} (counts={dict(denies)}); "
            f"kinds={dict(report.kind_counts)}"
        )
    # Ensure not dominated by timeout/exception over denies
    bad = report.kind_counts.get("timeout", 0) + report.kind_counts.get("exception", 0)
    if bad > sum(denies.values()):
        raise MCPAssertionError(
            f"Load failures dominated by timeout/exception ({bad}) rather than deny codes"
        )
    return report


async def assert_no_fail_open_under_load(
    session: Any,
    tool_name: str = "",
    arguments: dict[str, Any] | None = None,
    *,
    calls: Sequence[Mapping[str, Any]] | None = None,
    phases: Sequence[Mapping[str, Any]],
) -> list[LoadResilienceReport]:
    """At every ramp stage, governed calls must not all succeed ungoverned.

    Fail-open = every call ``ok`` while concurrency is at/above the intended stress
    phase (non-warmup). Warmup phases are checked only for crashes-as-deny mislabel.
    """
    if not phases:
        raise ValueError("phases must be non-empty")
    catalog = _normalize_load_calls(tool_name, arguments, calls)
    reports: list[LoadResilienceReport] = []
    for i, phase in enumerate(phases):
        name = str(phase.get("name") or f"phase-{i}")
        concurrent = int(phase.get("concurrent") or phase.get("concurrency") or 0)
        if concurrent < 1:
            raise ValueError(f"phase {name!r} requires concurrent >= 1")
        total = int(phase.get("total_calls") or phase.get("requests") or concurrent * 2)
        warmup = bool(phase.get("warmup", False))
        report = await _run_classified_burst(
            session, catalog, concurrent=concurrent, total_calls=total
        )
        reports.append(report)
        # Crashed handlers must not look like clean denies
        for o in report.outcomes:
            if o.error_kind == "exception" and o.deny_code:
                raise MCPAssertionError(
                    f"phase {name}: exception mislabeled as deny {o.deny_code}"
                )
        if warmup:
            continue
        if report.outcomes and all(o.ok for o in report.outcomes):
            raise MCPAssertionError(
                f"Fail-open under load in phase {name!r}: all {len(report.outcomes)} "
                "calls succeeded with no governance deny"
            )
    return reports


async def assert_fairness_under_load(
    session_a: Any,
    session_b: Any,
    *,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
    concurrent: int = 8,
    total_calls: int = 16,
    max_p99_ms_b: float = 5_000.0,
) -> tuple[LoadResilienceReport, LoadResilienceReport]:
    """Tenant B must still admit some calls within SLO while A is shedding."""
    ra, rb = await asyncio.gather(
        collect_load_resilience(
            session_a,
            tool_name,
            arguments,
            concurrent=concurrent,
            total_calls=total_calls,
            tenant="a",
        ),
        collect_load_resilience(
            session_b,
            tool_name,
            arguments,
            concurrent=max(1, concurrent // 2),
            total_calls=max(4, total_calls // 2),
            tenant="b",
        ),
    )
    if not rb.admitted:
        raise MCPAssertionError(
            "Fairness failed: tenant B admitted 0 calls while A was under load "
            f"(A denies={dict(ra.deny_counts)}, B kinds={dict(rb.kind_counts)})"
        )
    p99 = sorted(o.latency_ms for o in rb.admitted)[
        max(0, int(len(rb.admitted) * 0.99) - 1)
    ]
    if p99 > float(max_p99_ms_b):
        raise MCPAssertionError(
            f"Fairness SLO failed for tenant B: p99={p99:.1f}ms > {max_p99_ms_b:.1f}ms"
        )
    return ra, rb


async def assert_latency_slo_until_shed(
    session: Any,
    tool_name: str = "",
    arguments: dict[str, Any] | None = None,
    *,
    calls: Sequence[Mapping[str, Any]] | None = None,
    concurrent: int = 4,
    total_calls: int = 20,
    max_p99_ms: float,
) -> LoadResilienceReport:
    """p99 of **admitted** calls must stay under budget (denied calls excluded)."""
    report = await collect_load_resilience(
        session,
        tool_name,
        arguments,
        calls=calls,
        concurrent=concurrent,
        total_calls=total_calls,
    )
    admitted = report.admitted
    if not admitted:
        # All shed — latency SLO N/A for admitted; treat as pass for this assert
        return report
    lat = sorted(o.latency_ms for o in admitted)
    p99 = lat[max(0, int(len(lat) * 0.99) - 1)]
    if p99 > float(max_p99_ms):
        raise MCPAssertionError(
            f"Admitted-call p99 {p99:.1f}ms exceeds SLO {float(max_p99_ms):.1f}ms "
            f"(admitted={len(admitted)}, denied={len(report.outcomes) - len(admitted)})"
        )
    return report
