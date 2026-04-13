"""Report generators for the MCP Test Harness.

Provides console, JSON, and JUnit XML reporters that consume
:class:`~mcp_test_harness.models.TestRunResults` and produce
human-readable or machine-readable output.

Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6
"""

from __future__ import annotations

import json
import sys
from typing import Any, Protocol
from xml.sax.saxutils import escape as _xml_escape_base


def xml_escape(text: str) -> str:
    """Escape text for safe inclusion in XML attributes and element bodies."""
    return _xml_escape_base(text, {'"': "&quot;", "'": "&apos;"})

from mcp_test_harness.models import TestRunResults, TestResult, TestStatus


# ---------------------------------------------------------------------------
# Reporter protocol
# ---------------------------------------------------------------------------


class Reporter(Protocol):
    """Interface that all reporters must satisfy."""

    def generate(self, results: TestRunResults) -> str:
        """Return the formatted report as a string."""
        ...


# ---------------------------------------------------------------------------
# Console reporter  (Req 6.1)
# ---------------------------------------------------------------------------


class ConsoleReporter:
    """Human-readable summary printed to stdout.

    Includes per-test pass/fail lines and an aggregate summary with
    passed / failed / errored / skipped counts and total duration.
    """

    def generate(self, results: TestRunResults) -> str:
        lines: list[str] = []

        for tr in results.test_results:
            symbol = _status_symbol(tr.status)
            line = f"  {symbol} {tr.name} ({tr.duration_ms:.1f}ms)"
            lines.append(line)

            if tr.status in (TestStatus.FAILED, TestStatus.ERROR) and tr.error:
                lines.append(f"      {tr.error}")
            if tr.assertion_diff:
                for diff_line in tr.assertion_diff.splitlines():
                    lines.append(f"      {diff_line}")
            if tr.traceback and tr.status in (TestStatus.FAILED, TestStatus.ERROR):
                for tb_line in tr.traceback.splitlines():
                    lines.append(f"      {tb_line}")
            if tr.flaky:
                lines.append("      [!] flaky (passed on retry)")

        lines.append("")
        lines.append(
            f"{results.passed} passed, "
            f"{results.failed} failed, "
            f"{results.errored} errored, "
            f"{results.skipped} skipped"
        )
        lines.append(f"Total time: {results.total_duration_ms:.1f}ms")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# JSON reporter  (Req 6.2, 6.4, 6.5, 6.6)
# ---------------------------------------------------------------------------


class JSONReporter:
    """Full JSON report including metadata, per-test details, and durations."""

    def generate(self, results: TestRunResults) -> str:
        report: dict[str, Any] = {
            "metadata": {
                "harness_version": results.harness_version,
                "protocol_version": results.protocol_version,
                "server_capabilities": results.server_capabilities,
            },
            "summary": {
                "total": len(results.test_results),
                "passed": results.passed,
                "failed": results.failed,
                "errored": results.errored,
                "skipped": results.skipped,
                "timed_out": results.timed_out,
                "total_duration_ms": results.total_duration_ms,
            },
            "tests": [_test_result_to_dict(tr) for tr in results.test_results],
        }
        return json.dumps(report, indent=2, default=str)


# ---------------------------------------------------------------------------
# JUnit XML reporter  (Req 6.3, 6.4, 6.5)
# ---------------------------------------------------------------------------


class JUnitXMLReporter:
    """JUnit XML report compatible with GitHub Actions, Jenkins, and GitLab CI."""

    def generate(self, results: TestRunResults) -> str:
        tests = len(results.test_results)
        failures = results.failed
        errors = results.errored
        skipped = results.skipped
        time_s = results.total_duration_ms / 1000.0

        lines: list[str] = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            "<testsuites>",
            f'  <testsuite name="mcp-test" tests="{tests}" '
            f'failures="{failures}" errors="{errors}" '
            f'skipped="{skipped}" time="{time_s:.3f}">',
        ]

        for tr in results.test_results:
            tc_time = tr.duration_ms / 1000.0
            classname = xml_escape(tr.module)
            name = xml_escape(tr.name)
            lines.append(
                f'    <testcase name="{name}" classname="{classname}" '
                f'time="{tc_time:.3f}">'
            )

            if tr.status == TestStatus.FAILED:
                msg = xml_escape(tr.error or "assertion failure")
                body = _junit_failure_body(tr)
                lines.append(f'      <failure message="{msg}">{body}</failure>')
            elif tr.status == TestStatus.ERROR:
                msg = xml_escape(tr.error or "error")
                body = _junit_failure_body(tr)
                lines.append(f'      <error message="{msg}">{body}</error>')
            elif tr.status == TestStatus.SKIPPED:
                msg = xml_escape(tr.error or "skipped")
                lines.append(f'      <skipped message="{msg}" />')
            elif tr.status == TestStatus.TIMEOUT:
                msg = xml_escape(tr.error or "timeout")
                lines.append(f'      <error message="{msg}">Test timed out</error>')

            lines.append("    </testcase>")

        lines.append("  </testsuite>")
        lines.append("</testsuites>")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _status_symbol(status: TestStatus) -> str:
    """Return a short symbol for console display."""
    return {
        TestStatus.PASSED: "PASS",
        TestStatus.FAILED: "FAIL",
        TestStatus.ERROR: "ERR ",
        TestStatus.TIMEOUT: "TIME",
        TestStatus.SKIPPED: "SKIP",
    }.get(status, "?")


def _test_result_to_dict(tr: TestResult) -> dict[str, Any]:
    """Serialise a single TestResult for the JSON report."""
    d: dict[str, Any] = {
        "name": tr.name,
        "module": tr.module,
        "status": tr.status.value,
        "duration_ms": tr.duration_ms,
    }
    if tr.error is not None:
        d["error"] = tr.error
    if tr.traceback is not None:
        d["traceback"] = tr.traceback
    if tr.assertion_diff is not None:
        d["assertion_diff"] = tr.assertion_diff
    if tr.retry_count:
        d["retry_count"] = tr.retry_count
        d["attempt_results"] = [
            {
                "attempt": a.attempt,
                "status": a.status.value,
                "duration_ms": a.duration_ms,
                "error": a.error,
            }
            for a in tr.attempt_results
        ]
    if tr.flaky:
        d["flaky"] = True
    if tr.schema_violations:
        d["schema_violations"] = [
            {
                "json_path": v.json_path,
                "expected_type": v.expected_type,
                "actual_value": v.actual_value,
                "message": v.message,
            }
            for v in tr.schema_violations
        ]
    return d


def _junit_failure_body(tr: TestResult) -> str:
    """Build the text body for a JUnit <failure> or <error> element."""
    parts: list[str] = []
    if tr.assertion_diff:
        parts.append(tr.assertion_diff)
    if tr.traceback:
        parts.append(tr.traceback)
    return xml_escape("\n".join(parts)) if parts else ""
