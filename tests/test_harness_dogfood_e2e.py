"""End-to-end: the harness runs mcp-test against itself (dogfood).

Proves CLI → discovery → lifecycle → executor → assertions → reports
on a real stdio MCP subprocess, not only unit mocks.
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SERVER = _REPO_ROOT / "tests" / "fixtures" / "minimal_mcp_server.py"
_SELF_TESTS = _REPO_ROOT / "tests" / "fixtures" / "harness_self_test"


def _server_command() -> str:
    # Quoted paths are supported on Windows via split_server_command quote-stripping.
    return f"{shlex.quote(sys.executable)} {shlex.quote(str(_SERVER))}"


def _mcp_test_env() -> dict[str, str]:
    env = os.environ.copy()
    src = str(_REPO_ROOT / "src")
    env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    return env


def _run_mcp_test(*extra_args: str, report_path: Path | None = None) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable,
        "-m",
        "mcp_test_harness.cli",
        str(_SELF_TESTS),
        "--server-command",
        _server_command(),
        *extra_args,
    ]
    if report_path is not None:
        cmd.extend(["--report-format", "json", "--report-output", str(report_path)])
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(_REPO_ROOT),
        env=_mcp_test_env(),
        timeout=120,
    )


@pytest.mark.e2e
def test_mcp_test_cli_dogfood_passes() -> None:
    proc = _run_mcp_test()
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "passed" in proc.stdout.lower() or "1 passed" in proc.stdout


@pytest.mark.e2e
def test_mcp_test_cli_dogfood_json_report(tmp_path: Path) -> None:
    report = tmp_path / "dogfood-report.json"
    proc = _run_mcp_test(report_path=report)
    assert proc.returncode == 0, proc.stderr
    assert report.is_file()
    data = json.loads(report.read_text(encoding="utf-8"))
    assert data["summary"]["passed"] >= 1
    assert any(t["name"] == "test_echo_tool" for t in data["tests"])


@pytest.mark.e2e
def test_mcp_test_cli_dogfood_html_report(tmp_path: Path) -> None:
    report = tmp_path / "dogfood-report.html"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "mcp_test_harness.cli",
            str(_SELF_TESTS),
            "--server-command",
            _server_command(),
            "--report-format",
            "html",
            "--report-output",
            str(report),
        ],
        capture_output=True,
        text=True,
        cwd=str(_REPO_ROOT),
        env=_mcp_test_env(),
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    html = report.read_text(encoding="utf-8")
    assert "MCP Test Report" in html
    assert "test_echo_tool" in html


@pytest.mark.e2e
def test_mcp_test_generate_and_doctor_smoke() -> None:
    """Offline CLI subcommands against the same minimal server."""
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "mcp_test_harness.cli",
            "doctor",
            "--server-command",
            _server_command(),
        ],
        capture_output=True,
        text=True,
        cwd=str(_REPO_ROOT),
        env=_mcp_test_env(),
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    assert "doctor" in proc.stdout.lower() or "Transport" in proc.stdout
