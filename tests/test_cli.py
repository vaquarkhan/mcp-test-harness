"""Tests for mcp_test_harness.cli -- argument parsing, version, exit codes."""

from __future__ import annotations

import sys
from io import StringIO
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from mcp_test_harness.cli import _build_parser, _async_main, main
from mcp_test_harness.models import SessionResults, CaseStatus


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


class TestBuildParser:
    def test_default_test_path_is_none(self):
        parser = _build_parser()
        args = parser.parse_args([])
        assert args.test_path is None

    def test_positional_test_path(self):
        parser = _build_parser()
        args = parser.parse_args(["my_tests/"])
        assert args.test_path == "my_tests/"

    def test_server_command(self):
        parser = _build_parser()
        args = parser.parse_args(["--server-command", "python srv.py"])
        assert args.server_command == "python srv.py"

    def test_transport_choices(self):
        parser = _build_parser()
        for t in ("stdio", "sse", "http"):
            args = parser.parse_args(["--transport", t])
            assert args.transport == t

    def test_invalid_transport_exits(self):
        parser = _build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--transport", "grpc"])

    def test_config_flag(self):
        parser = _build_parser()
        args = parser.parse_args(["--config", "my.yaml"])
        assert args.config == "my.yaml"

    def test_verbose_flag(self):
        parser = _build_parser()
        args = parser.parse_args(["--verbose"])
        assert args.verbose is True

    def test_timeout_flag(self):
        parser = _build_parser()
        args = parser.parse_args(["--timeout", "60"])
        assert args.timeout == 60.0

    def test_parallel_flag(self):
        parser = _build_parser()
        args = parser.parse_args(["--parallel"])
        assert args.parallel is True

    def test_workers_flag(self):
        parser = _build_parser()
        args = parser.parse_args(["--workers", "8"])
        assert args.workers == 8

    def test_report_format_choices(self):
        parser = _build_parser()
        for fmt in ("json", "junit"):
            args = parser.parse_args(["--report-format", fmt])
            assert args.report_format == fmt

    def test_report_output(self):
        parser = _build_parser()
        args = parser.parse_args(["--report-output", "out.xml"])
        assert args.report_output == "out.xml"

    def test_update_snapshots(self):
        parser = _build_parser()
        args = parser.parse_args(["--update-snapshots"])
        assert args.update_snapshots is True

    def test_version_flag(self):
        parser = _build_parser()
        args = parser.parse_args(["--version"])
        assert args.version is True

    def test_k_filter(self):
        parser = _build_parser()
        args = parser.parse_args(["-k", "test_echo"])
        assert args.filter_name == "test_echo"

    def test_m_filter(self):
        parser = _build_parser()
        args = parser.parse_args(["-m", "smoke"])
        assert args.filter_marker == "smoke"

    def test_all_flags_combined(self):
        parser = _build_parser()
        args = parser.parse_args([
            "--server-command", "python s.py",
            "--transport", "sse",
            "--config", "c.yaml",
            "--verbose",
            "--timeout", "10",
            "--parallel",
            "--workers", "2",
            "--report-format", "json",
            "--report-output", "r.json",
            "--update-snapshots",
            "-k", "echo",
            "-m", "fast",
            "tests/",
        ])
        assert args.server_command == "python s.py"
        assert args.transport == "sse"
        assert args.test_path == "tests/"

    def test_watch_flag(self):
        parser = _build_parser()
        args = parser.parse_args(["--watch"])
        assert args.watch is True

    def test_watch_default_false(self):
        parser = _build_parser()
        assert parser.parse_args([]).watch is False


# ---------------------------------------------------------------------------
# _async_main -- version
# ---------------------------------------------------------------------------


class TestAsyncMainVersion:
    @pytest.mark.asyncio
    async def test_version_prints_and_returns_0(self, capsys):
        code = await _async_main(["--version"])
        assert code == 0
        captured = capsys.readouterr()
        assert "mcp-test" in captured.out
        assert "0.1.1" in captured.out


# ---------------------------------------------------------------------------
# _async_main -- config error
# ---------------------------------------------------------------------------


class TestAsyncMainConfigError:
    @pytest.mark.asyncio
    async def test_no_server_command_returns_2(self):
        code = await _async_main([])
        assert code == 2


# ---------------------------------------------------------------------------
# _async_main -- no tests discovered
# ---------------------------------------------------------------------------


class TestAsyncMainNoTests:
    @pytest.mark.asyncio
    async def test_no_tests_returns_0(self, tmp_path, capsys):
        empty_dir = tmp_path / "empty_tests"
        empty_dir.mkdir()
        code = await _async_main([
            "--server-command", "echo hi",
            str(empty_dir),
        ])
        assert code == 0
        captured = capsys.readouterr()
        assert "No tests discovered" in captured.out


# ---------------------------------------------------------------------------
# _async_main -- full run (mocked scheduler)
# ---------------------------------------------------------------------------


class TestAsyncMainFullRun:
    @pytest.mark.asyncio
    async def test_all_pass_returns_0(self, tmp_path, capsys):
        test_file = tmp_path / "test_ok.py"
        test_file.write_text("async def test_pass(): pass\n")

        mock_results = SessionResults(
            test_results=[],
            total_duration_ms=100.0,
            server_capabilities={},
            protocol_version="2024-11-05",
            harness_version="0.1.1",
            passed=1, failed=0, errored=0, skipped=0, timed_out=0,
        )

        with patch("mcp_test_harness.scheduler.HarnessScheduler") as MockSched:
            instance = MockSched.return_value
            instance.run_sequential = AsyncMock(return_value=mock_results)
            instance.run_parallel = AsyncMock(return_value=mock_results)

            code = await _async_main([
                "--server-command", "echo hi",
                str(tmp_path),
            ])

        assert code == 0

    @pytest.mark.asyncio
    async def test_failures_return_1(self, tmp_path):
        test_file = tmp_path / "test_fail.py"
        test_file.write_text("async def test_fail(): assert False\n")

        mock_results = SessionResults(
            test_results=[],
            total_duration_ms=50.0,
            server_capabilities={},
            protocol_version="",
            harness_version="0.1.1",
            passed=0, failed=1, errored=0, skipped=0, timed_out=0,
        )

        with patch("mcp_test_harness.scheduler.HarnessScheduler") as MockSched:
            instance = MockSched.return_value
            instance.run_sequential = AsyncMock(return_value=mock_results)

            code = await _async_main([
                "--server-command", "echo hi",
                str(tmp_path),
            ])

        assert code == 1

    @pytest.mark.asyncio
    async def test_errors_return_1(self, tmp_path):
        test_file = tmp_path / "test_err.py"
        test_file.write_text("async def test_err(): pass\n")

        mock_results = SessionResults(
            test_results=[],
            total_duration_ms=50.0,
            server_capabilities={},
            protocol_version="",
            harness_version="0.1.1",
            passed=0, failed=0, errored=1, skipped=0, timed_out=0,
        )

        with patch("mcp_test_harness.scheduler.HarnessScheduler") as MockSched:
            instance = MockSched.return_value
            instance.run_sequential = AsyncMock(return_value=mock_results)

            code = await _async_main([
                "--server-command", "echo hi",
                str(tmp_path),
            ])

        assert code == 1

    @pytest.mark.asyncio
    async def test_parallel_flag_uses_parallel_scheduler(self, tmp_path):
        test_file = tmp_path / "test_p.py"
        test_file.write_text("async def test_p(): pass\n")

        mock_results = SessionResults(
            test_results=[],
            total_duration_ms=50.0,
            server_capabilities={},
            protocol_version="",
            harness_version="0.1.1",
            passed=1, failed=0, errored=0, skipped=0, timed_out=0,
        )

        with patch("mcp_test_harness.scheduler.HarnessScheduler") as MockSched:
            instance = MockSched.return_value
            instance.run_parallel = AsyncMock(return_value=mock_results)
            instance.run_sequential = AsyncMock(return_value=mock_results)

            code = await _async_main([
                "--server-command", "echo hi",
                "--parallel",
                str(tmp_path),
            ])

        instance.run_parallel.assert_awaited_once()
        instance.run_sequential.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_report_output_written(self, tmp_path):
        test_file = tmp_path / "test_r.py"
        test_file.write_text("async def test_r(): pass\n")
        report_path = tmp_path / "report.json"

        mock_results = SessionResults(
            test_results=[],
            total_duration_ms=50.0,
            server_capabilities={},
            protocol_version="",
            harness_version="0.1.1",
            passed=1, failed=0, errored=0, skipped=0, timed_out=0,
        )

        with patch("mcp_test_harness.scheduler.HarnessScheduler") as MockSched:
            instance = MockSched.return_value
            instance.run_sequential = AsyncMock(return_value=mock_results)

            code = await _async_main([
                "--server-command", "echo hi",
                "--report-format", "json",
                "--report-output", str(report_path),
                str(tmp_path),
            ])

        assert code == 0
        assert report_path.exists()
        content = report_path.read_text()
        assert "harness_version" in content


# ---------------------------------------------------------------------------
# main() sync wrapper
# ---------------------------------------------------------------------------


class TestMainSync:
    def test_main_returns_int(self):
        code = main(["--version"])
        assert code == 0


# ---------------------------------------------------------------------------
# --list flag
# ---------------------------------------------------------------------------


class TestListFlag:
    def test_list_flag_parsed(self):
        parser = _build_parser()
        args = parser.parse_args(["--list"])
        assert args.list is True

    def test_list_default_false(self):
        parser = _build_parser()
        args = parser.parse_args([])
        assert args.list is False

    @pytest.mark.asyncio
    async def test_list_prints_tests_and_returns_0(self, tmp_path, capsys):
        test_file = tmp_path / "test_example.py"
        test_file.write_text(
            "async def test_alpha(): pass\nasync def test_beta(): pass\n"
        )

        code = await _async_main([
            "--server-command", "echo hi",
            "--list",
            str(tmp_path),
        ])

        assert code == 0
        captured = capsys.readouterr()
        assert "test_alpha" in captured.out
        assert "test_beta" in captured.out
        assert "::" in captured.out

    @pytest.mark.asyncio
    async def test_list_no_tests_returns_0(self, tmp_path, capsys):
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        code = await _async_main([
            "--server-command", "echo hi",
            "--list",
            str(empty_dir),
        ])

        assert code == 0
        captured = capsys.readouterr()
        assert "No tests discovered" in captured.out


# ---------------------------------------------------------------------------
# --watch + --list conflict
# ---------------------------------------------------------------------------


class TestWatchListConflict:
    @pytest.mark.asyncio
    async def test_watch_with_list_returns_2(self, tmp_path):
        f = tmp_path / "t.py"
        f.write_text("async def test_x(): pass\n")
        code = await _async_main(
            [
                "--server-command",
                "echo hi",
                "--watch",
                "--list",
                str(tmp_path),
            ],
        )
        assert code == 2


# ---------------------------------------------------------------------------
# --report-format html
# ---------------------------------------------------------------------------


class TestReportFormatHTML:
    def test_html_choice_accepted(self):
        parser = _build_parser()
        args = parser.parse_args(["--report-format", "html"])
        assert args.report_format == "html"

    @pytest.mark.asyncio
    async def test_html_report_written(self, tmp_path):
        test_file = tmp_path / "test_h.py"
        test_file.write_text("async def test_h(): pass\n")
        report_path = tmp_path / "report.html"

        mock_results = SessionResults(
            test_results=[],
            total_duration_ms=50.0,
            server_capabilities={},
            protocol_version="",
            harness_version="0.1.1",
            passed=1, failed=0, errored=0, skipped=0, timed_out=0,
        )

        with patch("mcp_test_harness.scheduler.HarnessScheduler") as MockSched:
            instance = MockSched.return_value
            instance.run_sequential = AsyncMock(return_value=mock_results)

            code = await _async_main([
                "--server-command", "echo hi",
                "--report-format", "html",
                "--report-output", str(report_path),
                str(tmp_path),
            ])

        assert code == 0
        assert report_path.exists()
        content = report_path.read_text()
        assert "<html" in content
        assert "MCP Test Report" in content
