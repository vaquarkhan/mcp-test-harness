"""HTML report generator for the MCP Test Harness.

Generates a self-contained HTML page with inline CSS -- no external
dependencies required.
"""

from __future__ import annotations

from html import escape as _html_escape

from mcp_test_harness.models import SessionResults, CaseResult, CaseStatus


def _status_label(status: CaseStatus) -> str:
    return {
        CaseStatus.PASSED: "PASS",
        CaseStatus.FAILED: "FAIL",
        CaseStatus.ERROR: "ERROR",
        CaseStatus.TIMEOUT: "TIMEOUT",
        CaseStatus.SKIPPED: "SKIP",
    }.get(status, "?")


def _status_class(status: CaseStatus) -> str:
    return {
        CaseStatus.PASSED: "pass",
        CaseStatus.FAILED: "fail",
        CaseStatus.ERROR: "error",
        CaseStatus.TIMEOUT: "error",
        CaseStatus.SKIPPED: "skip",
    }.get(status, "")


class HTMLReporter:
    """Generate a self-contained HTML test report."""

    def generate(self, results: SessionResults) -> str:
        rows = []
        for tr in results.test_results:
            detail = self._failure_detail(tr)
            rows.append(
                f'<tr class="{_status_class(tr.status)}">'
                f"<td>{_html_escape(tr.name)}</td>"
                f"<td>{_status_label(tr.status)}</td>"
                f"<td>{tr.duration_ms:.1f}ms</td>"
                f"<td><pre>{_html_escape(detail)}</pre></td>"
                f"</tr>"
            )

        test_rows = "\n".join(rows)

        return (
            "<!DOCTYPE html>\n"
            "<html lang=\"en\">\n"
            "<head><meta charset=\"utf-8\">\n"
            "<title>MCP Test Report</title>\n"
            "<style>\n"
            "body { font-family: sans-serif; margin: 2em; }\n"
            "table { border-collapse: collapse; width: 100%; margin-top: 1em; }\n"
            "th, td { border: 1px solid #ccc; padding: 6px 10px; text-align: left; }\n"
            "th { background: #f5f5f5; }\n"
            "tr.pass td:nth-child(2) { color: green; }\n"
            "tr.fail td:nth-child(2) { color: red; }\n"
            "tr.error td:nth-child(2) { color: orange; }\n"
            "tr.skip td:nth-child(2) { color: gray; }\n"
            "pre { margin: 0; white-space: pre-wrap; }\n"
            "</style>\n"
            "</head>\n"
            "<body>\n"
            "<h1>MCP Test Report</h1>\n"
            "<table>\n"
            "<tr><th>Metric</th><th>Value</th></tr>\n"
            f"<tr><td>Passed</td><td>{results.passed}</td></tr>\n"
            f"<tr><td>Failed</td><td>{results.failed}</td></tr>\n"
            f"<tr><td>Errored</td><td>{results.errored}</td></tr>\n"
            f"<tr><td>Skipped</td><td>{results.skipped}</td></tr>\n"
            f"<tr><td>Duration</td><td>{results.total_duration_ms:.1f}ms</td></tr>\n"
            "</table>\n"
            "<h2>Test Results</h2>\n"
            "<table>\n"
            "<tr><th>Name</th><th>Status</th><th>Duration</th><th>Details</th></tr>\n"
            f"{test_rows}\n"
            "</table>\n"
            "</body>\n"
            "</html>"
        )

    def _failure_detail(self, tr: CaseResult) -> str:
        parts: list[str] = []
        if tr.error:
            parts.append(tr.error)
        if tr.assertion_diff:
            parts.append(tr.assertion_diff)
        if tr.traceback:
            parts.append(tr.traceback)
        return "\n".join(parts)
