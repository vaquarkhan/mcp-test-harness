"""Tests for console encoding helpers and Windows-safe CLI help."""

from __future__ import annotations

import io
from unittest.mock import MagicMock, patch

from mcp_test_harness.cli import main
from mcp_test_harness.console_io import configure_stdio
from mcp_test_harness.pdf_export import run_export_pdf


def test_configure_stdio_reconfigures_when_supported() -> None:
    out = MagicMock()
    err = MagicMock()
    with patch("mcp_test_harness.console_io.sys.stdout", out), patch(
        "mcp_test_harness.console_io.sys.stderr", err
    ):
        configure_stdio()
    out.reconfigure.assert_called()
    err.reconfigure.assert_called()


def test_configure_stdio_tolerates_missing_reconfigure() -> None:
    class Plain:
        pass

    with patch("mcp_test_harness.console_io.sys.stdout", Plain()), patch(
        "mcp_test_harness.console_io.sys.stderr", Plain()
    ):
        configure_stdio()  # must not raise


def test_configure_stdio_tolerates_reconfigure_error() -> None:
    out = MagicMock()
    out.reconfigure.side_effect = OSError("locked")
    with patch("mcp_test_harness.console_io.sys.stdout", out), patch(
        "mcp_test_harness.console_io.sys.stderr", out
    ):
        configure_stdio()


def test_export_pdf_help_is_ascii() -> None:
    """BUG A: --help description must not contain non-ASCII arrows."""
    try:
        run_export_pdf(["--help"])
    except SystemExit as exc:
        assert exc.code == 0
    # Also ensure description string itself is ASCII
    import mcp_test_harness.pdf_export as pe

    src = pe.run_export_pdf.__doc__ or ""
    # Parse description from source file
    text = open(pe.__file__, encoding="utf-8").read()
    assert "\u2192" not in text.split("def run_export_pdf")[1].split("def ")[0]


def test_export_pdf_help_under_cp1252(capsys) -> None:
    """Simulate Windows redirected stdout (cp1252) for export-pdf --help."""
    buf = io.TextIOWrapper(io.BytesIO(), encoding="cp1252", errors="strict")
    with patch("sys.stdout", buf):
        # configure_stdio may upgrade encoding; still ensure help does not raise
        try:
            main(["export-pdf", "--help"])
        except SystemExit as exc:
            assert exc.code == 0
    # If reconfigure failed, writing help with arrow would have raised; we got here.
