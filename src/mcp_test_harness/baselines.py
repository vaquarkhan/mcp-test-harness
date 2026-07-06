"""Performance baseline load/save and regression checks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mcp_test_harness.assertions import MCPAssertionError


def load_baseline(path: str | Path) -> dict[str, Any]:
    """Load a JSON baseline file (``{"metrics": {key: ms}}``)."""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"Performance baseline not found: {p}")
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Baseline file must be a JSON object")
    return data


def save_baseline(path: str | Path, metrics: dict[str, float], *, metadata: dict[str, Any] | None = None) -> None:
    """Write metrics to a JSON baseline file."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {"metrics": dict(metrics)}
    if metadata:
        payload["metadata"] = metadata
    p.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def compare_metric(
    key: str,
    actual_ms: float,
    baseline: dict[str, Any],
    *,
    max_regression_pct: float = 15.0,
) -> None:
    """Fail when *actual_ms* exceeds baseline by more than *max_regression_pct*."""
    metrics = baseline.get("metrics", baseline)
    if key not in metrics:
        raise MCPAssertionError(f"Baseline has no metric key {key!r}")
    base_ms = float(metrics[key])
    if base_ms <= 0:
        if actual_ms > 0:
            raise MCPAssertionError(
                f"Metric {key!r}: baseline {base_ms}ms but measured {actual_ms:.1f}ms",
            )
        return
    limit = base_ms * (1.0 + max_regression_pct / 100.0)
    if actual_ms > limit:
        pct = 100.0 * (actual_ms - base_ms) / base_ms
        raise MCPAssertionError(
            f"Metric {key!r} regressed: {actual_ms:.1f}ms vs baseline {base_ms:.1f}ms "
            f"(+{pct:.1f}%, limit +{max_regression_pct:.0f}%)",
        )


async def assert_latency_within_baseline(
    session: Any,
    tool_name: str,
    arguments: dict[str, Any],
    baseline_path: str | Path,
    metric_key: str,
    *,
    max_regression_pct: float = 15.0,
    runs: int = 5,
    warmup: int = 1,
) -> None:
    """Measure ``call_tool`` latency and compare to a stored baseline."""
    import time

    for _ in range(warmup):
        await session.call_tool(tool_name, arguments)
    timings: list[float] = []
    for _ in range(max(1, runs)):
        t0 = time.perf_counter()
        await session.call_tool(tool_name, arguments)
        timings.append((time.perf_counter() - t0) * 1000.0)
    actual = max(timings)
    baseline = load_baseline(baseline_path)
    compare_metric(metric_key, actual, baseline, max_regression_pct=max_regression_pct)
