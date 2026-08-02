"""Browserless coverage for PDF/screenshot paths and H/I/J fix edge branches.

Keeps ``coverage report --fail-under=100`` honest on clean checkouts without
Chrome/Edge installed (mocked headless browser + negative-path unit tests).
"""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_test_harness.assertions import MCPAssertionError, assert_capabilities, _capability_subset
from mcp_test_harness.cli import _async_main
from mcp_test_harness.coverage import _unwrap_session, get_coverage, record_tool_call
from mcp_test_harness.html_reporter import (
    _format_started_at,
    _run_epoch_bounds,
)
from mcp_test_harness.models import CaseResult, CaseStatus, SessionResults
from mcp_test_harness.pdf_export import (
    _find_headless_browser,
    capture_html_screenshot,
    export_html_to_pdf,
)
from mcp_test_harness.record import (
    _call_is_error,
    _fill_missing_responses,
    _record_live,
    _response_is_mcp_error,
)
from tests.test_assertions import FakeSession
from tests.test_reporting import _make_results, _passed


# ---------------------------------------------------------------------------
# assertions._capability_subset failure branches (BUG I edges)
# ---------------------------------------------------------------------------


def test_capability_subset_expected_dict_actual_not_dict() -> None:
    assert _capability_subset({"listChanged": True}, True) is False


def test_capability_subset_missing_nested_key() -> None:
    assert _capability_subset({"a": 1, "b": 2}, {"a": 1}) is False


def test_capability_subset_nested_value_mismatch() -> None:
    assert _capability_subset({"tools": {"listChanged": True}}, {"tools": {"listChanged": False}}) is False


def test_assert_capabilities_nested_dict_vs_scalar_fails() -> None:
    session = FakeSession(capabilities={"tools": True})
    with pytest.raises(MCPAssertionError, match="capabilities mismatch"):
        asyncio.run(assert_capabilities(session, {"tools": {"listChanged": True}}))


# ---------------------------------------------------------------------------
# coverage._unwrap_session edges (BUG J)
# ---------------------------------------------------------------------------


def test_unwrap_session_breaks_on_cycle() -> None:
    a = SimpleNamespace()
    b = SimpleNamespace()
    a._inner = b
    b._inner = a
    # Cycle must terminate without infinite loop; result is one of the nodes.
    assert _unwrap_session(a) in (a, b)


def test_unwrap_session_stops_on_none_inner() -> None:
    leaf = SimpleNamespace()
    leaf._inner = None
    chain = SimpleNamespace(_inner=leaf)
    assert _unwrap_session(chain) is leaf
    assert _unwrap_session(leaf) is leaf


def test_coverage_record_via_none_inner_wrapper() -> None:
    wrap = SimpleNamespace(_inner=None)
    # When _inner is None, state lives on the wrapper itself
    record_tool_call(wrap, "echo")
    assert "echo" in get_coverage(wrap).tested_tools


# ---------------------------------------------------------------------------
# record.py reject-path / isError helpers + live codegen paths
# ---------------------------------------------------------------------------


def test_response_is_mcp_error_object_and_content_items() -> None:
    assert _response_is_mcp_error(SimpleNamespace(isError=True)) is True
    assert (
        _response_is_mcp_error(
            SimpleNamespace(isError=False, content=[SimpleNamespace(isError=True)])
        )
        is True
    )
    assert (
        _response_is_mcp_error(
            {"isError": False, "content": [{"type": "text", "isError": True}]}
        )
        is True
    )


def test_call_is_error_transport_and_mcp() -> None:
    assert _call_is_error({"error": "boom"}) is True
    assert _call_is_error({"response": {"isError": True}}) is True
    assert _call_is_error({"response": {"ok": True}}) is False


@pytest.mark.asyncio
async def test_record_live_calls_iserror_sets_error_message(capsys) -> None:
    tool = MagicMock()
    tool.name = "boom"
    tool.inputSchema = {"type": "object", "properties": {}}

    result = SimpleNamespace(isError=True, content=[])
    session = MagicMock()
    session.list_tools = AsyncMock(return_value=MagicMock(tools=[tool]))
    session.call_tool = AsyncMock(return_value=result)
    server = MagicMock(session=session)
    lifecycle = MagicMock()
    lifecycle.start = AsyncMock(return_value=server)
    lifecycle.shutdown = AsyncMock()

    cfg = MagicMock()
    with patch("mcp_test_harness.lifecycle.ServerLifecycleManager", return_value=lifecycle):
        calls = await _record_live(cfg, tool_filter=None, max_tools=None)

    assert calls[0]["error"] == "MCP tool returned isError=true"
    err = capsys.readouterr().err
    assert "isError" in err
    assert "assert_tool_rejects" in err


@pytest.mark.asyncio
async def test_fill_missing_responses_iserror_path(capsys) -> None:
    result = SimpleNamespace(isError=True, content=[])
    session = MagicMock()
    session.call_tool = AsyncMock(return_value=result)
    server = MagicMock(session=session)
    lifecycle = MagicMock()
    lifecycle.start = AsyncMock(return_value=server)
    lifecycle.shutdown = AsyncMock()

    calls = [{"tool": "boom", "arguments": {}}]
    cfg = MagicMock()
    with patch("mcp_test_harness.lifecycle.ServerLifecycleManager", return_value=lifecycle):
        out = await _fill_missing_responses(cfg, calls)

    assert out[0]["error"] == "MCP tool returned isError=true"
    assert "isError" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# pdf_export — mocked browser paths (no real Chrome/Edge)
# ---------------------------------------------------------------------------


class TestFindHeadlessBrowserBranches:
    def test_win32_which_hit(self) -> None:
        with (
            patch("mcp_test_harness.pdf_export.sys.platform", "win32"),
            patch("mcp_test_harness.pdf_export.shutil.which", return_value=r"C:\chrome.exe"),
            patch("pathlib.Path.is_file", return_value=False),
        ):
            found = _find_headless_browser()
        assert found == (r"C:\chrome.exe", [])

    def test_win32_common_install_path(self) -> None:
        with (
            patch("mcp_test_harness.pdf_export.sys.platform", "win32"),
            patch("mcp_test_harness.pdf_export.shutil.which", return_value=None),
            patch("pathlib.Path.is_file", return_value=True),
        ):
            found = _find_headless_browser()
        assert found is not None
        assert found[0].endswith("chrome.exe") or found[0].endswith("msedge.exe")

    def test_posix_which_hit(self) -> None:
        with (
            patch("mcp_test_harness.pdf_export.sys.platform", "linux"),
            patch(
                "mcp_test_harness.pdf_export.shutil.which",
                side_effect=lambda name: "/usr/bin/google-chrome" if name == "google-chrome" else None,
            ),
        ):
            found = _find_headless_browser()
        assert found == ("/usr/bin/google-chrome", [])


class TestExportHtmlToPdfFailurePaths:
    def test_timeout(self, tmp_path: Path) -> None:
        html = tmp_path / "r.html"
        html.write_text("<html></html>", encoding="utf-8")
        with (
            patch(
                "mcp_test_harness.pdf_export._find_headless_browser",
                return_value=("/usr/bin/chrome", []),
            ),
            patch(
                "mcp_test_harness.pdf_export.subprocess.run",
                side_effect=subprocess.TimeoutExpired(cmd="chrome", timeout=1),
            ),
        ):
            with pytest.raises(RuntimeError, match="timed out"):
                export_html_to_pdf(html, tmp_path / "out.pdf", timeout_sec=1)

    def test_nonzero_exit(self, tmp_path: Path) -> None:
        html = tmp_path / "r.html"
        html.write_text("<html></html>", encoding="utf-8")
        with (
            patch(
                "mcp_test_harness.pdf_export._find_headless_browser",
                return_value=("/usr/bin/chrome", []),
            ),
            patch(
                "mcp_test_harness.pdf_export.subprocess.run",
                return_value=MagicMock(returncode=1, stdout="", stderr="print failed"),
            ),
        ):
            with pytest.raises(RuntimeError, match="Headless print failed"):
                export_html_to_pdf(html, tmp_path / "out.pdf")


class TestCaptureHtmlScreenshotEdges:
    def test_missing_html(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="not found"):
            capture_html_screenshot(tmp_path / "missing.html", tmp_path / "out.png")

    def test_no_browser(self, tmp_path: Path) -> None:
        html = tmp_path / "r.html"
        html.write_text("<html></html>", encoding="utf-8")
        with patch("mcp_test_harness.pdf_export._find_headless_browser", return_value=None):
            with pytest.raises(RuntimeError, match="No headless"):
                capture_html_screenshot(html, tmp_path / "out.png")

    def test_timeout(self, tmp_path: Path) -> None:
        html = tmp_path / "r.html"
        html.write_text("<html></html>", encoding="utf-8")
        with (
            patch(
                "mcp_test_harness.pdf_export._find_headless_browser",
                return_value=("/usr/bin/chrome", []),
            ),
            patch(
                "mcp_test_harness.pdf_export.subprocess.run",
                side_effect=subprocess.TimeoutExpired(cmd="chrome", timeout=1),
            ),
        ):
            with pytest.raises(RuntimeError, match="timed out"):
                capture_html_screenshot(html, tmp_path / "out.png", timeout_sec=1)

    def test_nonzero_exit(self, tmp_path: Path) -> None:
        html = tmp_path / "r.html"
        html.write_text("<html></html>", encoding="utf-8")
        with (
            patch(
                "mcp_test_harness.pdf_export._find_headless_browser",
                return_value=("/usr/bin/chrome", []),
            ),
            patch(
                "mcp_test_harness.pdf_export.subprocess.run",
                return_value=MagicMock(returncode=2, stdout="", stderr="shot failed"),
            ),
        ):
            with pytest.raises(RuntimeError, match="Headless screenshot failed"):
                capture_html_screenshot(html, tmp_path / "out.png")


# ---------------------------------------------------------------------------
# cli.py HTML → PDF export path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_main_html_pdf_success_and_failure(tmp_path: Path, capsys) -> None:
    test_file = tmp_path / "test_ok.py"
    test_file.write_text("async def test_pass(): pass\n")
    report = tmp_path / "report.html"
    pdf = tmp_path / "report.pdf"

    mock_results = SessionResults(
        test_results=[],
        total_duration_ms=10.0,
        server_capabilities={},
        protocol_version="2024-11-05",
        harness_version="4.0.1",
        passed=1,
        failed=0,
        errored=0,
        skipped=0,
        timed_out=0,
    )

    with patch("mcp_test_harness.scheduler.HarnessScheduler") as MockSched:
        instance = MockSched.return_value
        instance.run_sequential = AsyncMock(return_value=mock_results)
        instance.run_parallel = AsyncMock(return_value=mock_results)

        with patch(
            "mcp_test_harness.pdf_export.export_html_to_pdf",
            return_value=None,
        ) as exp:
            code = await _async_main(
                [
                    "--server-command",
                    "echo hi",
                    str(tmp_path),
                    "--report-format",
                    "html",
                    "--report-output",
                    str(report),
                    "--pdf-output",
                    str(pdf),
                ]
            )
        assert code == 0
        assert report.is_file()
        exp.assert_called_once()

        with patch(
            "mcp_test_harness.pdf_export.export_html_to_pdf",
            side_effect=RuntimeError("no browser"),
        ):
            code = await _async_main(
                [
                    "--server-command",
                    "echo hi",
                    str(tmp_path),
                    "--report-format",
                    "html",
                    "--report-output",
                    str(report),
                    "--pdf-output",
                    str(pdf),
                ]
            )
        assert code == 0
        err = capsys.readouterr().err
        assert "PDF export failed" in err


# ---------------------------------------------------------------------------
# html_reporter date helpers — exception / fallback branches
# ---------------------------------------------------------------------------


def test_format_started_at_invalid_falls_back() -> None:
    bad = "not-a-real-timestamp"
    assert _format_started_at(bad) == bad[:19]


def test_run_epoch_bounds_from_tests_when_session_times_missing() -> None:
    tr = _passed("test_a")
    tr.started_at = "2024-12-15T10:01:30+00:00"
    tr.duration_ms = 250.0
    run = SessionResults(
        test_results=[tr],
        total_duration_ms=250.0,
        server_capabilities={},
        protocol_version="",
        harness_version="4.0.1",
        passed=1,
        failed=0,
        errored=0,
        skipped=0,
        timed_out=0,
        started_at=None,
        finished_at=None,
    )
    start, end = _run_epoch_bounds(run)
    assert start is not None
    assert end is not None
    assert end >= start


def test_run_epoch_bounds_end_from_duration_when_finished_missing() -> None:
    run = _make_results([_passed()])
    run.finished_at = None
    start, end = _run_epoch_bounds(run)
    assert start is not None
    assert end == start + int(run.total_duration_ms)


def test_run_epoch_bounds_end_from_test_when_only_started_invalid() -> None:
    tr = CaseResult(
        name="t",
        module="m.py",
        status=CaseStatus.PASSED,
        duration_ms=100.0,
        started_at="2024-12-15T11:00:00+00:00",
    )
    run = SessionResults(
        test_results=[tr],
        total_duration_ms=0.0,
        server_capabilities={},
        protocol_version="",
        harness_version="4.0.1",
        passed=1,
        failed=0,
        errored=0,
        skipped=0,
        timed_out=0,
        started_at="bad",
        finished_at="also-bad",
    )
    start, end = _run_epoch_bounds(run)
    assert start is not None
    assert end is not None
