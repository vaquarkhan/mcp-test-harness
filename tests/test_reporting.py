"""Unit tests for mcp_test_harness.reporting."""

from __future__ import annotations

import json
from xml.etree import ElementTree as ET

import pytest

from mcp_test_harness.models import (
    AttemptResult,
    SchemaViolation,
    CaseResult,
    SessionResults,
    CaseStatus,
)
from mcp_test_harness.reporting import (
    _Ansi,
    ConsoleReporter,
    JSONReporter,
    JUnitXMLReporter,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_results(
    test_results: list[CaseResult] | None = None,
    *,
    total_duration_ms: float = 150.0,
) -> SessionResults:
    """Build a minimal SessionResults for testing."""
    results = test_results or []
    return SessionResults(
        test_results=results,
        total_duration_ms=total_duration_ms,
        server_capabilities={"tools": True, "resources": True},
        protocol_version="2025-03-26",
        harness_version="1.1.0",
        passed=sum(1 for r in results if r.status == CaseStatus.PASSED),
        failed=sum(1 for r in results if r.status == CaseStatus.FAILED),
        errored=sum(1 for r in results if r.status == CaseStatus.ERROR),
        skipped=sum(1 for r in results if r.status == CaseStatus.SKIPPED),
        timed_out=sum(1 for r in results if r.status == CaseStatus.TIMEOUT),
        started_at="2024-12-15T10:00:00+00:00",
        finished_at="2024-12-15T10:02:00+00:00",
        environment={
            "python_version": "3.12.0",
            "platform": "linux-test",
            "cwd": "/tmp",
            "server_command": "python -m demo",
            "transport": "stdio",
        },
    )


def _passed(name: str = "test_ok", duration: float = 10.0) -> CaseResult:
    return CaseResult(
        name=name, module="tests/test_example.py",
        status=CaseStatus.PASSED, duration_ms=duration,
    )


def _failed(
    name: str = "test_fail",
    error: str = "expected 1 got 2",
    diff: str | None = "- 1\n+ 2",
    tb: str | None = "Traceback ...",
) -> CaseResult:
    return CaseResult(
        name=name, module="tests/test_example.py",
        status=CaseStatus.FAILED, duration_ms=20.0,
        error=error, traceback=tb, assertion_diff=diff,
    )


def _errored(name: str = "test_err") -> CaseResult:
    return CaseResult(
        name=name, module="tests/test_example.py",
        status=CaseStatus.ERROR, duration_ms=5.0,
        error="RuntimeError: boom", traceback="Traceback ...",
    )


def _skipped(name: str = "test_skip") -> CaseResult:
    return CaseResult(
        name=name, module="tests/test_example.py",
        status=CaseStatus.SKIPPED, duration_ms=0.0,
        error="not ready",
    )


def _timed_out(name: str = "test_slow") -> CaseResult:
    return CaseResult(
        name=name, module="tests/test_example.py",
        status=CaseStatus.TIMEOUT, duration_ms=30000.0,
        error="Test exceeded 30s timeout",
    )


# ---------------------------------------------------------------------------
# ConsoleReporter
# ---------------------------------------------------------------------------


class TestConsoleReporter:
    def test_summary_counts(self):
        run = _make_results([_passed(), _failed(), _errored(), _skipped()])
        out = ConsoleReporter().generate(run)

        assert "1 passed" in out
        assert "1 failed" in out
        assert "1 errored" in out
        assert "1 skipped" in out

    def test_total_duration(self):
        run = _make_results([], total_duration_ms=1234.5)
        out = ConsoleReporter().generate(run)
        assert "1234.5ms" in out

    def test_per_test_duration(self):
        run = _make_results([_passed("test_a", duration=42.3)])
        out = ConsoleReporter().generate(run)
        assert "42.3ms" in out

    def test_failure_details_shown(self):
        run = _make_results([_failed(error="bad value", diff="- a\n+ b")])
        out = ConsoleReporter().generate(run)
        assert "bad value" in out
        assert "- a" in out
        assert "+ b" in out

    def test_flaky_warning(self):
        tr = _passed("test_flaky")
        tr.flaky = True
        run = _make_results([tr])
        out = ConsoleReporter().generate(run)
        assert "flaky" in out

    def test_empty_run(self):
        run = _make_results([])
        out = ConsoleReporter().generate(run)
        assert "0 passed" in out

    def test_console_color_mode_covers_all_status_colours(self, monkeypatch):
        class _TTY:
            def isatty(self):
                return True

        monkeypatch.setattr("mcp_test_harness.reporting.sys.stdout", _TTY())
        run = _make_results([
            _passed("p"),
            _failed("f"),
            _errored("e"),
            _skipped("s"),
            _timed_out("t"),
        ])
        out = ConsoleReporter().generate(run)
        assert "FAILURES" in out
        # ANSI escape appears in colored output
        assert "\x1b[" in out

    def test_ansi_for_status_unknown_returns_empty(self):
        assert _Ansi.for_status(object()) == ""


# ---------------------------------------------------------------------------
# JSONReporter
# ---------------------------------------------------------------------------


class TestJSONReporter:
    def test_valid_json(self):
        run = _make_results([_passed(), _failed()])
        raw = JSONReporter().generate(run)
        data = json.loads(raw)
        assert isinstance(data, dict)

    def test_metadata_fields(self):
        """Req 6.6 -- metadata includes harness_version, protocol_version, server_capabilities."""
        run = _make_results([_passed()])
        data = json.loads(JSONReporter().generate(run))

        meta = data["metadata"]
        assert meta["harness_version"] == "1.1.0"
        assert meta["protocol_version"] == "2025-03-26"
        assert meta["server_capabilities"] == {"tools": True, "resources": True}
        assert "started_at" in meta
        assert "finished_at" in meta
        assert "environment" in data
        assert "python_version" in data["environment"]
        assert "duration_percentiles_ms" in data["summary"]

    def test_summary_counts(self):
        run = _make_results([_passed(), _failed(), _skipped()])
        data = json.loads(JSONReporter().generate(run))

        assert data["summary"]["passed"] == 1
        assert data["summary"]["failed"] == 1
        assert data["summary"]["skipped"] == 1
        assert data["summary"]["total"] == 3

    def test_per_test_details(self):
        """Req 6.4 -- failed tests include error, traceback, assertion_diff."""
        run = _make_results([_failed(error="oops", diff="- x\n+ y", tb="Traceback ...")])
        data = json.loads(JSONReporter().generate(run))

        t = data["tests"][0]
        assert t["status"] == "failed"
        assert t["error"] == "oops"
        assert t["traceback"] == "Traceback ..."
        assert t["assertion_diff"] == "- x\n+ y"

    def test_duration_in_ms(self):
        """Req 6.5 -- durations in milliseconds."""
        run = _make_results([_passed("t", duration=42.5)], total_duration_ms=100.0)
        data = json.loads(JSONReporter().generate(run))

        assert data["summary"]["total_duration_ms"] == 100.0
        assert data["tests"][0]["duration_ms"] == 42.5

    def test_retry_info_included(self):
        tr = CaseResult(
            name="test_flaky", module="m.py",
            status=CaseStatus.PASSED, duration_ms=50.0,
            retry_count=2, flaky=True,
            attempt_results=[
                AttemptResult(attempt=1, status=CaseStatus.FAILED, duration_ms=10.0, error="fail"),
                AttemptResult(attempt=2, status=CaseStatus.FAILED, duration_ms=10.0, error="fail"),
                AttemptResult(attempt=3, status=CaseStatus.PASSED, duration_ms=30.0),
            ],
        )
        run = _make_results([tr])
        data = json.loads(JSONReporter().generate(run))

        t = data["tests"][0]
        assert t["retry_count"] == 2
        assert t["flaky"] is True
        assert len(t["attempt_results"]) == 3

    def test_schema_violations_included(self):
        tr = _passed()
        tr.schema_violations = [
            SchemaViolation(
                json_path="$.result.content",
                expected_type="array",
                actual_value="string",
                message="Expected array",
            )
        ]
        run = _make_results([tr])
        data = json.loads(JSONReporter().generate(run))

        assert len(data["tests"][0]["schema_violations"]) == 1
        assert data["tests"][0]["schema_violations"][0]["json_path"] == "$.result.content"

    def test_test_tags_and_started_at_included(self):
        tr = _passed("tagged")
        tr.tags = ["smoke", "perf"]
        tr.started_at = "2026-01-01T00:00:00+00:00"
        data = json.loads(JSONReporter().generate(_make_results([tr])))
        t = data["tests"][0]
        assert t["tags"] == ["smoke", "perf"]
        assert t["started_at"] == "2026-01-01T00:00:00+00:00"


# ---------------------------------------------------------------------------
# JUnitXMLReporter
# ---------------------------------------------------------------------------


class TestJUnitXMLReporter:
    def test_valid_xml(self):
        run = _make_results([_passed(), _failed(), _errored(), _skipped(), _timed_out()])
        xml_str = JUnitXMLReporter().generate(run)
        root = ET.fromstring(xml_str)
        assert root.tag == "testsuites"

    def test_testsuite_attributes(self):
        run = _make_results([_passed(), _failed()], total_duration_ms=500.0)
        root = ET.fromstring(JUnitXMLReporter().generate(run))
        suite = root.find("testsuite")

        assert suite is not None
        assert suite.get("tests") == "2"
        assert suite.get("failures") == "1"
        assert suite.get("time") == "0.500"

    def test_passed_testcase_no_children(self):
        run = _make_results([_passed()])
        root = ET.fromstring(JUnitXMLReporter().generate(run))
        tc = root.find(".//testcase")

        assert tc is not None
        assert len(list(tc)) == 0  # no failure/error children

    def test_failed_testcase_has_failure(self):
        run = _make_results([_failed(error="bad", diff="- a\n+ b", tb="TB")])
        root = ET.fromstring(JUnitXMLReporter().generate(run))
        tc = root.find(".//testcase")
        failure = tc.find("failure")

        assert failure is not None
        assert failure.get("message") == "bad"
        assert "- a" in (failure.text or "")

    def test_errored_testcase_has_error(self):
        run = _make_results([_errored()])
        root = ET.fromstring(JUnitXMLReporter().generate(run))
        tc = root.find(".//testcase")
        error = tc.find("error")

        assert error is not None

    def test_skipped_testcase(self):
        run = _make_results([_skipped()])
        root = ET.fromstring(JUnitXMLReporter().generate(run))
        tc = root.find(".//testcase")
        skipped = tc.find("skipped")

        assert skipped is not None
        assert skipped.get("message") == "not ready"

    def test_timeout_testcase_has_error(self):
        run = _make_results([_timed_out()])
        root = ET.fromstring(JUnitXMLReporter().generate(run))
        tc = root.find(".//testcase")
        error = tc.find("error")

        assert error is not None
        assert "timeout" in (error.get("message") or "").lower()

    def test_per_test_duration_in_seconds(self):
        """Req 6.5 -- per-test time attribute in seconds."""
        run = _make_results([_passed("t", duration=1500.0)])
        root = ET.fromstring(JUnitXMLReporter().generate(run))
        tc = root.find(".//testcase")

        assert tc is not None
        assert tc.get("time") == "1.500"

    def test_xml_escaping(self):
        """Special characters in names/errors are XML-escaped."""
        tr = _failed(name='test_<special>&"chars', error='val < 0 & "bad"')
        run = _make_results([tr])
        xml_str = JUnitXMLReporter().generate(run)
        # Should parse without error -- proves escaping is correct
        root = ET.fromstring(xml_str)
        tc = root.find(".//testcase")
        assert tc is not None

    def test_classname_uses_forward_slashes(self):
        tr = _passed("t")
        tr.module = "tests\\demo\\a.py"
        tr.file = "tests/demo/a.py"
        run = _make_results([tr])
        xml_str = JUnitXMLReporter().generate(run)
        tc = ET.fromstring(xml_str).find(".//testcase")
        assert tc is not None
        assert tc.get("classname") == "tests/demo/a.py"
        assert "\\\\" not in (tc.get("classname") or "")

    def test_testsuite_has_timestamp_and_properties(self):
        run = _make_results([_passed()])
        root = ET.fromstring(JUnitXMLReporter().generate(run))
        suite = root.find("testsuite")
        assert suite is not None
        assert suite.get("timestamp")
        assert suite.get("hostname")
        assert suite.find("properties") is not None

    def test_testcase_tags_written_as_properties(self):
        tr = _passed("tag_case")
        tr.tags = ["smoke"]
        root = ET.fromstring(JUnitXMLReporter().generate(_make_results([tr])))
        props = root.findall(".//testcase/properties/property")
        assert props
        assert props[0].get("name") == "tag"
        assert props[0].get("value") == "smoke"


# ---------------------------------------------------------------------------
# HTMLReporter
# ---------------------------------------------------------------------------

from mcp_test_harness.html_reporter import HTMLReporter


class TestHTMLReporter:
    def test_generates_valid_html(self):
        run = _make_results([_passed(), _failed()])
        html = HTMLReporter().generate(run)
        assert "<!DOCTYPE html>" in html
        assert "<html" in html
        assert "</html>" in html

    def test_summary_counts(self):
        run = _make_results([_passed(), _failed(), _errored(), _skipped()])
        html = HTMLReporter().generate(run)
        # Summary table should contain the counts
        assert ">1<" in html  # at least one count of 1

    def test_test_names_in_output(self):
        run = _make_results([_passed("test_alpha"), _failed("test_beta")])
        html = HTMLReporter().generate(run)
        assert "test_alpha" in html
        assert "test_beta" in html

    def test_failure_details_shown(self):
        run = _make_results([_failed(error="bad value", diff="- a\n+ b")])
        html = HTMLReporter().generate(run)
        assert "bad value" in html
        assert "- a" in html

    def test_empty_run(self):
        run = _make_results([])
        html = HTMLReporter().generate(run)
        assert "MCP Test Report" in html
        assert "0" in html

    def test_html_escaping(self):
        tr = _failed(name="test_<script>", error="x < 0 & y > 1")
        run = _make_results([tr])
        html = HTMLReporter().generate(run)
        # User-controlled test name and error must be escaped (report may include <script> for its own UI).
        assert "test_&lt;script&gt;" in html
        assert "&lt;script&gt;" in html
        assert "x &lt; 0 &amp; y &gt; 1" in html

    def test_duration_shown(self):
        run = _make_results([_passed("t", duration=42.3)], total_duration_ms=100.5)
        html = HTMLReporter().generate(run)
        assert "42.3" in html
        assert "100.5" in html

    def test_html_includes_attempts_and_schema_details(self):
        tr = _failed(error="boom", diff=None, tb=None)
        tr.attempt_results = [
            AttemptResult(attempt=1, status=CaseStatus.FAILED, duration_ms=10.0, error="e1"),
            AttemptResult(attempt=2, status=CaseStatus.PASSED, duration_ms=9.0, error=None),
        ]
        tr.retry_count = 1
        tr.flaky = True
        tr.schema_violations = [
            SchemaViolation(
                json_path="$.x",
                expected_type="string",
                actual_value=1,
                message="wrong type",
            )
        ]
        html = HTMLReporter().generate(_make_results([tr]))
        assert "Attempts:" in html
        assert "schema:" in html
        assert "Flaky: passed after 1 retry" in html

    def test_html_capability_summary_overflow(self):
        run = _make_results([_passed()])
        run.server_capabilities = {f"k{i}": True for i in range(20)}
        html = HTMLReporter().generate(run)
        assert "+12 more" in html or "more" in html

    def test_html_capability_summary_truncates_with_ellipsis(self):
        run = _make_results([_passed()])
        # Long key names force truncation path
        run.server_capabilities = {("key_" + ("x" * 40) + str(i)): True for i in range(12)}
        html = HTMLReporter().generate(run)
        assert "…" in html
