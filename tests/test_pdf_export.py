"""Tests for HTML → PDF export."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcp_test_harness.html_reporter import GITHUB_REPO, PRODUCT_SITE, HTMLReporter
from mcp_test_harness.pdf_export import (
    _find_headless_browser,
    _html_file_uri,
    export_html_to_pdf,
    run_export_pdf,
)
from tests.test_reporting import _make_results, _passed


class TestHtmlFileUri:
    def test_resolves_to_file_uri(self, tmp_path: Path) -> None:
        html = tmp_path / "report.html"
        html.write_text("<html></html>", encoding="utf-8")
        uri = _html_file_uri(html)
        assert uri.startswith("file://")
        assert "report.html" in uri


class TestFindHeadlessBrowser:
    def test_returns_none_when_no_browser(self) -> None:
        with patch("mcp_test_harness.pdf_export.shutil.which", return_value=None):
            with patch("pathlib.Path.is_file", return_value=False):
                assert _find_headless_browser() is None


class TestExportHtmlToPdf:
    def test_missing_html_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="not found"):
            export_html_to_pdf(tmp_path / "missing.html", tmp_path / "out.pdf")

    def test_no_browser_raises(self, tmp_path: Path) -> None:
        html = tmp_path / "r.html"
        html.write_text("<html></html>", encoding="utf-8")
        with patch("mcp_test_harness.pdf_export._find_headless_browser", return_value=None):
            with pytest.raises(RuntimeError, match="No headless"):
                export_html_to_pdf(html, tmp_path / "out.pdf")

    def test_success_when_browser_prints(self, tmp_path: Path) -> None:
        html = tmp_path / "r.html"
        html.write_text("<html></html>", encoding="utf-8")
        pdf = tmp_path / "out.pdf"

        def fake_run(cmd, **kwargs):
            pdf.write_bytes(b"%PDF-1.4 fake")
            return MagicMock(returncode=0, stdout="", stderr="")

        with patch(
            "mcp_test_harness.pdf_export._find_headless_browser",
            return_value=("/usr/bin/chrome", []),
        ):
            with patch("mcp_test_harness.pdf_export.subprocess.run", side_effect=fake_run):
                export_html_to_pdf(html, pdf)
        assert pdf.is_file()


class TestRunExportPdf:
    def test_cli_success(self, tmp_path: Path) -> None:
        html = tmp_path / "r.html"
        html.write_text("<html></html>", encoding="utf-8")
        with patch("mcp_test_harness.pdf_export.export_html_to_pdf") as exp:
            code = run_export_pdf([str(html)])
        assert code == 0
        exp.assert_called_once()

    def test_cli_failure(self, tmp_path: Path) -> None:
        html = tmp_path / "r.html"
        html.write_text("<html></html>", encoding="utf-8")
        with patch(
            "mcp_test_harness.pdf_export.export_html_to_pdf",
            side_effect=RuntimeError("boom"),
        ):
            code = run_export_pdf([str(html)])
        assert code == 1


class TestHtmlReporterBranding:
    def test_product_site_and_pdf_controls(self) -> None:
        html = HTMLReporter().generate(_make_results([_passed()]))
        assert PRODUCT_SITE in html
        assert GITHUB_REPO in html
        assert "mcp-export-pdf" in html
        assert "Save as PDF" in html
        assert "@media print" in html
        assert "export-pdf" in html
