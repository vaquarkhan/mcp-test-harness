"""Write the static HTML sample using the real HTML reporter.

Run from the repository root:

    python examples/feature-demo/reports/build_sample_html.py
"""

from __future__ import annotations

from pathlib import Path

from mcp_test_harness.html_reporter import HTMLReporter
from mcp_test_harness.models import CaseResult, CaseStatus, SessionResults


def _repo_root() -> Path:
    # .../examples/feature-demo/reports/ -> parents[2] = repository root
    return Path(__file__).resolve().parent.parents[2]


def main() -> None:
    results = SessionResults(
        test_results=[
            CaseResult(
                name="test_echo_tool",
                module="tests/test_server.py",
                status=CaseStatus.PASSED,
                duration_ms=12.4,
            ),
            CaseResult(
                name="test_tool_schema_matches",
                module="tests/test_server.py",
                status=CaseStatus.PASSED,
                duration_ms=8.1,
            ),
            CaseResult(
                name="test_bad_snapshot",
                module="tests/test_regression.py",
                status=CaseStatus.FAILED,
                duration_ms=25.0,
                error="Snapshot mismatch for tool 'list'",
                assertion_diff="--- expected\n+++ actual\n- {'count': 1}\n+ {'count': 2}",
            ),
            CaseResult(
                name="test_optional_prompt",
                module="tests/test_prompts.py",
                status=CaseStatus.SKIPPED,
                duration_ms=0.0,
                error="server has no prompts capability",
            ),
        ],
        total_duration_ms=1842.6,
        server_capabilities={"tools": True, "resources": True, "logging": True},
        protocol_version="2025-03-26",
        harness_version="1.0.0",
        passed=2,
        failed=1,
        errored=0,
        skipped=1,
        timed_out=0,
    )
    out = _repo_root() / "examples" / "feature-demo" / "reports" / "sample_mcp_test_report.html"
    out.write_text(HTMLReporter().generate(results), encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
