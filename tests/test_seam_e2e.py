"""Seam / round-trip / contract e2e tests.

These catch the H/I/J class of bugs that 100% line coverage + isolated unit
tests miss: generated code must parse and run; documented contracts must hold
against a real server; coverage must be populated after tools are called;
init output must validate and run.
"""

from __future__ import annotations

import ast
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

from mcp_test_harness.config import validate_config_file
from mcp_test_harness.record import render_recorded_module

_REPO_ROOT = Path(__file__).resolve().parents[1]
_RICH = _REPO_ROOT / "tests" / "fixtures" / "rich_mcp_server.py"
_SEAM_TESTS = _REPO_ROOT / "tests" / "fixtures" / "harness_seam_test"


def _server_command(server: Path = _RICH) -> str:
    return f"{shlex.quote(sys.executable)} {shlex.quote(str(server))}"


def _env() -> dict[str, str]:
    env = os.environ.copy()
    src = str(_REPO_ROOT / "src")
    env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    return env


def _run(*args: str, cwd: Path | None = None, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "mcp_test_harness.cli", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(cwd or _REPO_ROOT),
        env=_env(),
        timeout=timeout,
    )


@pytest.mark.e2e
def test_record_output_is_valid_python_and_runs(tmp_path: Path) -> None:
    """BUG H class: if we emit code, a test must execute that code."""
    out = tmp_path / "test_recorded_seam.py"
    proc = _run(
        "record",
        "--server-command",
        _server_command(),
        "--out",
        str(out),
        "--tools",
        "echo,add,boom",
        "--force",
    )
    assert proc.returncode == 0, proc.stderr
    src = out.read_text(encoding="utf-8")
    ast.parse(src)  # must be valid Python (not substring-only checks)
    compile(src, str(out), "exec")
    assert "assert_tool_call" in src
    assert "assert_tool_rejects" in src or "boom" in src.lower() or "rejects" in src

    # Round-trip: run the generated suite against the same server
    run = _run(
        str(out),
        "--server-command",
        _server_command(),
        "--report-format",
        "json",
        "--report-output",
        str(tmp_path / "rec.json"),
    )
    # boom reject-path should pass; happy-paths should pass
    assert run.returncode == 0, run.stdout + run.stderr


@pytest.mark.e2e
def test_render_recorded_module_ast_parse_property() -> None:
    """Property: every render_recorded_module output must ast.parse."""
    samples = [
        [{"tool": "echo", "arguments": {"text": "a"}, "response": {"ok": True}}],
        [
            {
                "tool": "boom",
                "arguments": {},
                "response": {"isError": True, "content": [{"type": "text", "text": "x"}]},
            }
        ],
        [
            {"tool": "a", "arguments": {}, "response": {"r": 1}},
            {"tool": "a", "arguments": {"x": 1}, "response": {"r": 2}},
            {"tool": "fail", "arguments": {}, "error": "transport"},
        ],
    ]
    for calls in samples:
        src = render_recorded_module(calls)
        ast.parse(src)


@pytest.mark.e2e
def test_readme_contracts_and_coverage_populated(tmp_path: Path) -> None:
    """BUG I/J class: README contracts + coverage map against a real server."""
    report = tmp_path / "seam.json"
    proc = _run(
        str(_SEAM_TESTS),
        "--server-command",
        _server_command(),
        "--report-format",
        "json",
        "--report-output",
        str(report),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    data = json.loads(report.read_text(encoding="utf-8"))
    assert data["summary"]["failed"] == 0
    assert data["summary"]["errored"] == 0
    assert data["summary"]["passed"] >= 4

    cov = data.get("coverage") or {}
    tested = (cov.get("tested") or {}).get("tools") or []
    assert tested, "coverage.tested.tools must be non-empty after tool calls (BUG J)"
    assert "echo" in tested or "add" in tested

    # Conformance should be able to see tools_tested > 0
    us = data.get("unified_summary") or {}
    conf = us.get("conformance") or {}
    # At least Protocol; Covered requires tools_tested which we just asserted
    assert conf.get("name") in ("Protocol", "Covered", "Secure", "Resilient", "Boot")
    summary_cov = (cov.get("summary") or {})
    assert int(summary_cov.get("tools_tested") or 0) > 0


@pytest.mark.e2e
def test_onboarding_init_then_run(tmp_path: Path) -> None:
    """First-run seam: init → validate → run must not green-pass on broken scaffold."""
    # Point init at rich server so generated starter tests can pass list_tools etc.
    proc = _run(
        "init",
        "--dir",
        str(tmp_path),
        "--server-command",
        _server_command(),
        "--force",
    )
    assert proc.returncode == 0, proc.stderr
    cfg = tmp_path / "mcp-test.yaml"
    assert cfg.is_file()
    assert validate_config_file(cfg) == []
    txt = cfg.read_text(encoding="utf-8")
    assert "test_dirs:" not in txt
    assert "test:" in txt and "dirs:" in txt

    # Starter scaffold tests are mostly comments; list_tools test should pass
    run = _run(
        "--config",
        str(cfg),
        str(tmp_path / "tests"),
        cwd=tmp_path,
    )
    # Empty discovery is exit 5; scaffold writes a real test file
    assert run.returncode in (0, 1), run.stdout + run.stderr
    assert "No tests discovered" not in (run.stderr + run.stdout)
    # Prefer green: list_tools starter should pass
    assert run.returncode == 0, run.stdout + run.stderr


@pytest.mark.e2e
def test_cli_help_under_redirected_cp1252() -> None:
    """Encoding seam: redirected Windows cp1252 stdout must not crash --help."""
    env = _env()
    env["PYTHONUTF8"] = "0"
    env["PYTHONIOENCODING"] = "cp1252"
    for sub in ("export-pdf", "doctor", "experiment", "try"):
        proc = subprocess.run(
            [sys.executable, "-m", "mcp_test_harness.cli", sub, "--help"],
            capture_output=True,
            text=True,
            encoding="cp1252",
            errors="strict",
            cwd=str(_REPO_ROOT),
            env=env,
            timeout=60,
        )
        assert proc.returncode == 0, f"{sub}: {proc.stderr}"
