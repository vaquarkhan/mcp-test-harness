"""Write the static HTML sample using the real HTML reporter.

Run from the repository root:

    python examples/feature-demo/reports/build_sample_html.py
"""

from __future__ import annotations

from pathlib import Path

from mcp_test_harness.coverage import CoverageState, coverage_to_dict
from mcp_test_harness.html_reporter import HTMLReporter
from mcp_test_harness.models import (
    AttemptResult,
    CaseResult,
    CaseStatus,
    SchemaViolation,
    SessionResults,
)
from mcp_test_harness.unified_report import build_unified_summary


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parents[2]


def _echo_trace() -> dict:
    return {
        "event_count": 4,
        "stdio_pollution": ["WARN: deprecated config key in stderr"],
        "events": [
            {
                "t_ms": 0.8,
                "direction": "request",
                "method": "tools/call",
                "bytes": 84,
                "payload": {"name": "echo", "arguments": {"message": "ping"}},
            },
            {
                "t_ms": 3.2,
                "direction": "response",
                "method": "tools/call",
                "bytes": 120,
                "payload": {"content": [{"type": "text", "text": "ping"}]},
            },
            {
                "t_ms": 4.1,
                "direction": "request",
                "method": "tools/call",
                "bytes": 92,
                "payload": {"name": "echo", "arguments": {"message": ""}},
            },
            {
                "t_ms": 5.0,
                "direction": "error",
                "method": "tools/call",
                "bytes": 64,
                "payload": {"isError": True, "message": "message must be non-empty"},
                "stdio_pollution": True,
            },
        ],
    }


def _stamp_started_at(tests: list[CaseResult], run_start: str, run_end: str) -> None:
    """Spread started_at across the run window for date-filter demos."""
    from datetime import datetime, timezone

    t0 = datetime.fromisoformat(run_start.replace("Z", "+00:00"))
    t1 = datetime.fromisoformat(run_end.replace("Z", "+00:00"))
    span_ms = max(int((t1 - t0).total_seconds() * 1000), 1)
    n = len(tests)
    for i, tr in enumerate(tests):
        if tr.started_at:
            continue
        offset_ms = int(span_ms * i / max(n - 1, 1))
        ts = t0.timestamp() * 1000 + offset_ms
        tr.started_at = (
            datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )


def _demo_results() -> SessionResults:
    tests: list[CaseResult] = [
        # --- tests/test_server.py (functional) ---
        CaseResult(
            name="test_echo_tool_returns_message",
            module="tests/test_server.py",
            file="tests/test_server.py",
            status=CaseStatus.PASSED,
            duration_ms=12.4,
            tags=["smoke", "functional"],
            started_at="2026-07-06T20:10:01.120Z",
        ),
        CaseResult(
            name="test_tool_schema_matches_openapi",
            module="tests/test_server.py",
            file="tests/test_server.py",
            status=CaseStatus.PASSED,
            duration_ms=48.2,
            tags=["functional"],
        ),
        CaseResult(
            name="test_list_tools_includes_echo",
            module="tests/test_server.py",
            file="tests/test_server.py",
            status=CaseStatus.PASSED,
            duration_ms=6.8,
            tags=["smoke"],
        ),
        CaseResult(
            name="test_echo_rejects_empty_payload",
            module="tests/test_server.py",
            file="tests/test_server.py",
            status=CaseStatus.FAILED,
            duration_ms=31.5,
            tags=["functional"],
            error="Tool 'echo' response mismatch",
            assertion_diff=(
                "--- expected\n+++ actual\n"
                "@@ -1,3 +1,3 @@\n"
                ' [{"text": "validation error", "isError": true}]\n'
                '+[{"text": "ok", "isError": false}]'
            ),
            mcp_trace=_echo_trace(),
        ),
        # --- tests/test_regression.py ---
        CaseResult(
            name="test_report_snapshot_stable",
            module="tests/test_regression.py",
            file="tests/test_regression.py",
            status=CaseStatus.FAILED,
            duration_ms=89.0,
            tags=["regression", "snapshot"],
            error="Snapshot mismatch for 'generate_report'",
            assertion_diff="--- expected\n+++ actual\n- {'version': '2.0.0'}\n+ {'version': '2.0.1'}",
        ),
        CaseResult(
            name="test_tool_idempotent_calculate",
            module="tests/test_regression.py",
            file="tests/test_regression.py",
            status=CaseStatus.PASSED,
            duration_ms=156.3,
            tags=["regression"],
        ),
        # --- tests/test_security.py ---
        CaseResult(
            name="test_injection_payloads_blocked",
            module="tests/test_security.py",
            file="tests/test_security.py",
            status=CaseStatus.PASSED,
            duration_ms=420.7,
            tags=["security"],
        ),
        CaseResult(
            name="test_no_secret_leak_in_logs",
            module="tests/test_security.py",
            file="tests/test_security.py",
            status=CaseStatus.FAILED,
            duration_ms=55.1,
            tags=["security"],
            error="Tool 'get_config' output matched secret pattern(s): aws_key",
        ),
        CaseResult(
            name="test_path_traversal_blocked",
            module="tests/test_security.py",
            file="tests/test_security.py",
            status=CaseStatus.PASSED,
            duration_ms=210.4,
            tags=["security"],
        ),
        # --- tests/test_performance.py ---
        CaseResult(
            name="test_echo_latency_p95_under_slo",
            module="tests/test_performance.py",
            file="tests/test_performance.py",
            status=CaseStatus.PASSED,
            duration_ms=1240.0,
            tags=["perf", "latency"],
        ),
        CaseResult(
            name="test_throughput_min_rps",
            module="tests/test_performance.py",
            file="tests/test_performance.py",
            status=CaseStatus.FAILED,
            duration_ms=980.0,
            tags=["perf", "throughput"],
            error="Throughput 42.1 rps below minimum 50.0 rps (p99=312ms)",
        ),
        # --- tests/test_resiliency.py ---
        CaseResult(
            name="test_degrades_gracefully_on_bad_args",
            module="tests/test_resiliency.py",
            file="tests/test_resiliency.py",
            status=CaseStatus.PASSED,
            duration_ms=72.0,
            tags=["resiliency", "chaos"],
        ),
        CaseResult(
            name="test_chaos_delay_tolerance",
            module="tests/test_resiliency.py",
            file="tests/test_resiliency.py",
            status=CaseStatus.PASSED,
            duration_ms=145.0,
            tags=["chaos", "chaos:delay", "resiliency"],
        ),
        CaseResult(
            name="test_chaos_503_unavailable",
            module="tests/test_resiliency.py",
            file="tests/test_resiliency.py",
            status=CaseStatus.FAILED,
            duration_ms=88.0,
            tags=["chaos", "chaos:503", "resiliency"],
            error="ChaosFaultError: simulated 503 Service Unavailable",
        ),
        CaseResult(
            name="test_chaos_schema_drift_probe",
            module="tests/test_resiliency.py",
            file="tests/test_resiliency.py",
            status=CaseStatus.PASSED,
            duration_ms=62.0,
            tags=["chaos", "chaos:schema_drift"],
        ),
        CaseResult(
            name="test_survives_server_restart",
            module="tests/test_resiliency.py",
            file="tests/test_resiliency.py",
            status=CaseStatus.ERROR,
            duration_ms=18.0,
            tags=["resiliency"],
            error="ConnectionResetError: MCP server process exited with code 1",
            traceback="Traceback (most recent call last):\n  File tests/test_resiliency.py, line 44\n    await assert_tool_call(...)",
        ),
        CaseResult(
            name="test_flaky_resource_read",
            module="tests/test_resiliency.py",
            file="tests/test_resiliency.py",
            status=CaseStatus.PASSED,
            duration_ms=340.0,
            tags=["resiliency"],
            flaky=True,
            retry_count=2,
            attempt_results=[
                AttemptResult(1, CaseStatus.TIMEOUT, 5000.0, error="read_resource timed out"),
                AttemptResult(2, CaseStatus.ERROR, 120.0, error="503 from upstream"),
                AttemptResult(3, CaseStatus.PASSED, 88.0, error=None),
            ],
        ),
        CaseResult(
            name="test_schema_probe_strict",
            module="tests/test_schema.py",
            file="tests/test_schema.py",
            status=CaseStatus.FAILED,
            duration_ms=44.0,
            tags=["functional"],
            error="Schema validation failed for tool 'search'",
            schema_violations=[
                SchemaViolation(
                    json_path="$.arguments.limit",
                    expected_type="integer",
                    actual_value="ten",
                    message="limit must be an integer",
                ),
            ],
        ),
        # --- skipped ---
        CaseResult(
            name="test_prompts_when_available",
            module="tests/test_prompts.py",
            file="tests/test_prompts.py",
            status=CaseStatus.SKIPPED,
            duration_ms=0.0,
            tags=["functional"],
            error="server has no prompts capability",
        ),
        CaseResult(
            name="test_optional_bedrock_pack",
            module="tests/test_prompts.py",
            file="tests/test_prompts.py",
            status=CaseStatus.SKIPPED,
            duration_ms=0.0,
            tags=["integration"],
            error="optional extra mcp-test-harness-bedrock not installed",
        ),
        CaseResult(
            name="test_long_running_export",
            module="tests/test_performance.py",
            file="tests/test_performance.py",
            status=CaseStatus.TIMEOUT,
            duration_ms=30000.0,
            tags=["perf"],
            error="Test exceeded timeout of 30000ms",
        ),
    ]

    run_start = "2026-07-06T20:10:00.000Z"
    run_end = "2026-07-06T20:10:02.340Z"
    _stamp_started_at(tests, run_start, run_end)

    passed = sum(1 for t in tests if t.status == CaseStatus.PASSED)
    failed = sum(1 for t in tests if t.status == CaseStatus.FAILED)
    errored = sum(1 for t in tests if t.status == CaseStatus.ERROR)
    skipped = sum(1 for t in tests if t.status == CaseStatus.SKIPPED)
    timed_out = sum(1 for t in tests if t.status == CaseStatus.TIMEOUT)

    cov_state = CoverageState(
        advertised_tools={"echo", "search", "get_config", "calculate", "export_report"},
        advertised_resources={"file:///config.json", "file:///health"},
        advertised_prompts={"summarize"},
        tested_tools={"echo", "search", "get_config", "calculate"},
        tested_resources={"file:///config.json"},
        tested_prompts=set(),
        auth_tested_tools={"echo", "search"},
    )
    coverage = coverage_to_dict(cov_state)

    results = SessionResults(
        test_results=tests,
        total_duration_ms=2340.0,
        server_capabilities={
            "tools": {"listChanged": True},
            "resources": {"subscribe": False},
            "logging": {},
            "prompts": {},
        },
        protocol_version="2025-03-26",
        harness_version="3.0.0",
        passed=passed,
        failed=failed,
        errored=errored,
        skipped=skipped,
        timed_out=timed_out,
        started_at=run_start,
        finished_at=run_end,
        environment={
            "python_version": "3.12.4",
            "platform": "Windows-11-amd64",
            "cwd": "C:/demo/mcp-server",
            "server_command": "python -m my_mcp_server --transport stdio",
            "transport": "stdio",
            "bastion_paired": "CI verifies · Bastion protects production",
        },
        coverage=coverage,
    )
    results.unified_summary = build_unified_summary(results, coverage)
    return results


def main() -> None:
    results = _demo_results()
    root = _repo_root()
    html = HTMLReporter().generate(results)
    destinations = (
        root / "examples" / "feature-demo" / "reports" / "sample_mcp_test_report.html",
        root / "html" / "reports" / "sample_mcp_test_report.html",
    )
    for out in destinations:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html, encoding="utf-8")
        print(f"Wrote {out}")
    print(
        f"  {results.passed} passed, {results.failed} failed, {results.errored} errored, "
        f"{results.skipped} skipped, {results.timed_out} timeout "
        f"({len(results.test_results)} tests)"
    )
    print("Validate UI:")
    print("  python -m http.server 8765 -d html/reports")
    print("  open http://localhost:8765/sample_mcp_test_report.html")
    print("  try: status chips · date From/To · duration min/max · Export CSV · Theme")
    try:
        from mcp_test_harness.pdf_export import capture_html_screenshot

        for dest in (
            root / "docs" / "images" / "html-dashboard.png",
            root / "html" / "assets" / "images" / "html-dashboard.png",
        ):
            capture_html_screenshot(out, dest)
            print(f"Wrote screenshot {dest}")
    except (OSError, RuntimeError) as exc:
        print(f"Screenshot skipped: {exc}")


if __name__ == "__main__":
    main()
