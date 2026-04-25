"""Report generators for the MCP Test Harness.

Provides console, JSON, and JUnit XML reporters that consume
:class:`~mcp_test_harness.models.SessionResults` and produce
human-readable or machine-readable output.

Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6
"""

from __future__ import annotations

import json
import socket
import statistics
import sys
from datetime import datetime, timezone
from typing import Any, Protocol
from xml.sax.saxutils import escape as _xml_escape_base


def xml_escape(text: str) -> str:
    """Escape text for safe inclusion in XML attributes and element bodies."""
    return _xml_escape_base(text, {'"': "&quot;", "'": "&apos;"})

from mcp_test_harness.models import SessionResults, CaseResult, CaseStatus


# ---------------------------------------------------------------------------
# Reporter protocol
# ---------------------------------------------------------------------------


class Reporter(Protocol):
    """Interface that all reporters must satisfy."""

    def generate(self, results: SessionResults) -> str:
        """Return the formatted report as a string."""
        ...


# ---------------------------------------------------------------------------
# Console colours (TTY)
# ---------------------------------------------------------------------------


class _NoColor:
    red = green = yellow = reset = bold = ""

    @staticmethod
    def for_status(_status: CaseStatus) -> str:
        return ""


class _Ansi:
    red = "\033[31m"
    green = "\033[32m"
    yellow = "\033[33m"
    reset = "\033[0m"
    bold = "\033[1m"

    @staticmethod
    def for_status(status: CaseStatus) -> str:
        if status == CaseStatus.PASSED:
            return "\033[32m"
        if status in (CaseStatus.FAILED, CaseStatus.ERROR, CaseStatus.TIMEOUT):
            return "\033[31m"
        if status == CaseStatus.SKIPPED:
            return "\033[90m"
        return ""


def _status_pretty(status: CaseStatus) -> str:
    return {
        CaseStatus.PASSED: "PASS",
        CaseStatus.FAILED: "FAIL",
        CaseStatus.ERROR: "ERR",
        CaseStatus.TIMEOUT: "TIME",
        CaseStatus.SKIPPED: "SKIP",
    }.get(status, "?")


# ---------------------------------------------------------------------------
# Console reporter  (Req 6.1)
# ---------------------------------------------------------------------------


class ConsoleReporter:
    """Human-readable summary printed to stdout.

    Includes per-test pass/fail lines and an aggregate summary with
    passed / failed / errored / skipped counts and total duration.
    When stdout is a TTY, pass/fail lines use ANSI colors; failures are
    repeated in a final ``FAILURES`` block (``pytest``-style).
    """

    def generate(self, results: SessionResults) -> str:
        use_color = sys.stdout.isatty()
        c = _Ansi() if use_color else _NoColor()

        lines: list[str] = []
        failure_blocks: list[str] = []

        for tr in results.test_results:
            sym = _status_symbol(tr.status)
            st = f"{c.bold}{_status_pretty(tr.status)}{c.reset}" if use_color else _status_pretty(tr.status)
            col = c.for_status(tr.status)
            name_part = f"{col}{tr.name}{c.reset}" if use_color else tr.name
            line = f"  {st}  {name_part}  ({tr.duration_ms:.1f}ms)"
            lines.append(line)

            if tr.status in (CaseStatus.FAILED, CaseStatus.ERROR) and tr.error:
                msg = f"      {tr.error}"
                lines.append(f"{c.red}{msg}{c.reset}" if use_color else msg)
            if tr.assertion_diff:
                for diff_line in tr.assertion_diff.splitlines():
                    lines.append(f"      {diff_line}")
            if tr.traceback and tr.status in (CaseStatus.FAILED, CaseStatus.ERROR):
                for tb_line in tr.traceback.splitlines():
                    lines.append(f"      {tb_line}")
            if tr.flaky:
                fk = "      [!] flaky (passed on retry)"
                lines.append(f"{c.yellow}{fk}{c.reset}" if use_color else fk)

            if tr.status in (CaseStatus.FAILED, CaseStatus.ERROR, CaseStatus.TIMEOUT):
                fb: list[str] = [f"{tr.file or tr.name}"]
                fb.append(f"  {tr.name} — {tr.error or tr.status.value}")
                if tr.assertion_diff:
                    fb.append(tr.assertion_diff)
                if tr.traceback:
                    fb.append(tr.traceback)
                failure_blocks.append("\n".join(fb))

        lines.append("")
        # Summary line stays plain ASCII so log parsers and tests stay stable.
        lines.append(
            f"{results.passed} passed, "
            f"{results.failed} failed, "
            f"{results.errored} errored, "
            f"{results.skipped} skipped"
        )
        lines.append(f"Total time: {results.total_duration_ms:.1f}ms")

        if failure_blocks:
            lines.append("")
            lines.append("=" * 40)
            lines.append("FAILURES" if not use_color else f"{c.bold}{c.red}FAILURES{c.reset}")
            for block in failure_blocks:
                lines.append("-" * 20)
                lines.append(block)
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# JSON reporter  (Req 6.2, 6.4, 6.5, 6.6)
# ---------------------------------------------------------------------------


class JSONReporter:
    """Full JSON report including metadata, per-test details, and durations."""

    def generate(self, results: SessionResults) -> str:
        durs = [tr.duration_ms for tr in results.test_results if tr.status != CaseStatus.SKIPPED]
        pcts = _suite_duration_percentiles(durs)
        report: dict[str, Any] = {
            "metadata": {
                "harness_version": results.harness_version,
                "protocol_version": results.protocol_version,
                "server_capabilities": results.server_capabilities,
                "started_at": results.started_at or _utc_now_iso(),
                "finished_at": results.finished_at or _utc_now_iso(),
            },
            "environment": {**dict(results.environment), "report_generated_at": _utc_now_iso()},
            "summary": {
                "total": len(results.test_results),
                "passed": results.passed,
                "failed": results.failed,
                "errored": results.errored,
                "skipped": results.skipped,
                "timed_out": results.timed_out,
                "total_duration_ms": results.total_duration_ms,
                "duration_percentiles_ms": pcts,
            },
            "tests": [_test_result_to_dict(tr) for tr in results.test_results],
        }
        return json.dumps(report, indent=2, default=str)


# ---------------------------------------------------------------------------
# JUnit XML reporter  (Req 6.3, 6.4, 6.5)
# ---------------------------------------------------------------------------


class JUnitXMLReporter:
    """JUnit XML report compatible with GitHub Actions, Jenkins, and GitLab CI."""

    def generate(self, results: SessionResults) -> str:
        tests = len(results.test_results)
        failures = results.failed
        errors = results.errored + results.timed_out
        skipped = results.skipped
        time_s = results.total_duration_ms / 1000.0
        ts = xml_escape(
            (results.finished_at or results.started_at) or _utc_now_iso()
        )
        host = xml_escape(socket.gethostname())
        suite_name = "mcp-test"

        lines: list[str] = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            "<testsuites>",
            f'  <testsuite name="{suite_name}" tests="{tests}" '
            f'failures="{failures}" errors="{errors}" '
            f'skipped="{skipped}" time="{time_s:.3f}" timestamp="{ts}" hostname="{host}">',
        ]
        lines.append("    <properties>")
        for k, v in {
            "harness_version": results.harness_version,
            "mcp_protocol_version": results.protocol_version,
            "transport": results.environment.get("transport", ""),
            "server_command": results.environment.get("server_command", ""),
            "run_started_at": results.started_at,
            "run_finished_at": results.finished_at,
        }.items():
            lines.append(
                f'      <property name="{xml_escape(k)}" value="{xml_escape(str(v))}" />'
            )
        lines.append("    </properties>")

        for tr in results.test_results:
            tc_time = tr.duration_ms / 1000.0
            classname = xml_escape((tr.file or tr.module).replace("\\", "/"))
            name = xml_escape(tr.name)
            lines.append(
                f'    <testcase name="{name}" classname="{classname}" '
                f'time="{tc_time:.3f}">'
            )
            if tr.tags:
                lines.append("      <properties>")
                for tag in tr.tags:
                    lines.append(
                        f'        <property name="tag" value="{xml_escape(tag)}" />'
                    )
                lines.append("      </properties>")

            if tr.status == CaseStatus.FAILED:
                msg = xml_escape(tr.error or "assertion failure")
                body = _junit_failure_body(tr)
                lines.append(f'      <failure message="{msg}">{body}</failure>')
            elif tr.status == CaseStatus.ERROR:
                msg = xml_escape(tr.error or "error")
                body = _junit_failure_body(tr)
                lines.append(f'      <error message="{msg}">{body}</error>')
            elif tr.status == CaseStatus.SKIPPED:
                msg = xml_escape(tr.error or "skipped")
                lines.append(f'      <skipped message="{msg}" />')
            elif tr.status == CaseStatus.TIMEOUT:
                msg = xml_escape(tr.error or "timeout")
                lines.append(f'      <error message="{msg}">Test timed out</error>')

            lines.append("    </testcase>")

        lines.append("  </testsuite>")
        lines.append("</testsuites>")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _status_symbol(status: CaseStatus) -> str:
    """Return a short symbol for console display."""
    return {
        CaseStatus.PASSED: "PASS",
        CaseStatus.FAILED: "FAIL",
        CaseStatus.ERROR: "ERR ",
        CaseStatus.TIMEOUT: "TIME",
        CaseStatus.SKIPPED: "SKIP",
    }.get(status, "?")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _suite_duration_percentiles(durations_ms: list[float]) -> dict[str, float]:
    """p50 / p95 / p99 over non-skipped test durations (ms)."""
    if not durations_ms:
        return {"p50_ms": 0.0, "p95_ms": 0.0, "p99_ms": 0.0}
    s = sorted(durations_ms)
    n = len(s)

    def nearest_rank(p: float) -> float:
        if n == 1:
            return s[0]
        # Clamp to [0, n-1] defensively.
        k = max(0, min(n - 1, int((p / 100.0) * n)))
        return s[k]

    return {
        "p50_ms": round(statistics.median(s), 2),
        "p95_ms": round(nearest_rank(95.0), 2),
        "p99_ms": round(nearest_rank(99.0), 2),
    }


def _test_result_to_dict(tr: CaseResult) -> dict[str, Any]:
    """Serialise a single CaseResult for the JSON report."""
    f = tr.file or tr.module.replace("\\", "/")
    d: dict[str, Any] = {
        "name": tr.name,
        "module": tr.module,
        "file": f,
        "status": tr.status.value,
        "duration_ms": tr.duration_ms,
    }
    if tr.tags:
        d["tags"] = list(tr.tags)
    if tr.started_at:
        d["started_at"] = tr.started_at
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


def _junit_failure_body(tr: CaseResult) -> str:
    """Build the text body for a JUnit <failure> or <error> element."""
    parts: list[str] = []
    if tr.assertion_diff:
        parts.append(tr.assertion_diff)
    if tr.traceback:
        parts.append(tr.traceback)
    return xml_escape("\n".join(parts)) if parts else ""
