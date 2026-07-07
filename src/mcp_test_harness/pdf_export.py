"""Export HTML test reports to PDF (JMeter-style summary).

Uses a headless Chromium browser when available (Chrome, Edge, Chromium).
Falls back to instructions for browser **Save as PDF** via the report toolbar.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def _html_file_uri(path: Path) -> str:
    """Return a ``file://`` URI suitable for headless print."""
    resolved = path.resolve()
    # pathlib.as_uri() is correct on Windows (file:///C:/...)
    return resolved.as_uri()


def _find_headless_browser() -> tuple[str, list[str]] | None:
    """Return (executable, extra args) for the first usable headless browser."""
    candidates: list[tuple[str, list[str]]] = []
    if sys.platform == "win32":
        for name in ("msedge", "chrome", "chromium"):
            exe = shutil.which(name)
            if exe:
                candidates.append((exe, []))
        # Common Windows install paths when not on PATH
        for path in (
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        ):
            if Path(path).is_file():
                candidates.append((path, []))
    else:
        for name in ("google-chrome", "chromium", "chromium-browser", "chrome"):
            exe = shutil.which(name)
            if exe:
                candidates.append((exe, []))
    return candidates[0] if candidates else None


def export_html_to_pdf(
    html_path: Path,
    pdf_path: Path,
    *,
    timeout_sec: float = 60.0,
) -> None:
    """Render *html_path* to *pdf_path* using headless Chrome/Edge.

    Raises ``RuntimeError`` when no browser is found or print fails.
    """
    html_path = html_path.resolve()
    if not html_path.is_file():
        raise FileNotFoundError(f"HTML report not found: {html_path}")

    pdf_path = pdf_path.resolve()
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    browser = _find_headless_browser()
    if browser is None:
        raise RuntimeError(
            "No headless Chrome/Edge/Chromium found. "
            "Open the HTML report in a browser and use **Save as PDF**, "
            "or install Chrome/Edge and retry `mcp-test export-pdf`."
        )

    exe, extra = browser
    file_uri = _html_file_uri(html_path)
    cmd = [
        exe,
        *extra,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--run-all-compositor-stages-before-draw",
        "--virtual-time-budget=10000",
        f"--print-to-pdf={pdf_path}",
        file_uri,
    ]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"PDF export timed out after {timeout_sec:g}s") from exc

    if proc.returncode != 0 or not pdf_path.is_file():
        err = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(
            f"Headless print failed (exit {proc.returncode}). {err}".strip()
        )


def capture_html_screenshot(
    html_path: Path,
    png_path: Path,
    *,
    width: int = 1440,
    height: int = 2200,
    timeout_sec: float = 60.0,
) -> None:
    """Capture a PNG screenshot of an HTML report using headless Chrome/Edge."""
    html_path = html_path.resolve()
    if not html_path.is_file():
        raise FileNotFoundError(f"HTML report not found: {html_path}")

    png_path = png_path.resolve()
    png_path.parent.mkdir(parents=True, exist_ok=True)

    browser = _find_headless_browser()
    if browser is None:
        raise RuntimeError(
            "No headless Chrome/Edge/Chromium found for screenshot capture."
        )

    exe, extra = browser
    file_uri = _html_file_uri(html_path)
    cmd = [
        exe,
        *extra,
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        f"--window-size={width},{height}",
        f"--screenshot={png_path}",
        file_uri,
    ]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"Screenshot timed out after {timeout_sec:g}s") from exc

    if proc.returncode != 0 or not png_path.is_file():
        err = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(
            f"Headless screenshot failed (exit {proc.returncode}). {err}".strip()
        )


def run_export_pdf(argv: list[str]) -> int:
    """Entry point: ``mcp-test export-pdf REPORT.html [-o OUT.pdf]``."""
    parser = argparse.ArgumentParser(
        prog="mcp-test export-pdf",
        description=(
            "Convert an MCP Test Harness HTML report to PDF using headless Chrome/Edge. "
            "Similar to JMeter HTML dashboard → PDF summary export."
        ),
    )
    parser.add_argument(
        "html_report",
        help="Path to a self-contained HTML report (from --report-format html)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output PDF path (default: same name as HTML with .pdf extension)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="Seconds to wait for headless browser (default: 60)",
    )
    args = parser.parse_args(argv)

    html_path = Path(args.html_report)
    pdf_path = Path(args.output) if args.output else html_path.with_suffix(".pdf")

    try:
        export_html_to_pdf(html_path, pdf_path, timeout_sec=args.timeout)
    except (OSError, RuntimeError) as exc:
        print(f"export-pdf: {exc}", file=sys.stderr)
        return 1

    print(f"PDF written to {pdf_path}")
    return 0
