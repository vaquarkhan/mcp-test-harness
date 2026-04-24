"""Tests for mcp_test_harness.scaffold (mcp-test init)."""

from __future__ import annotations

from pathlib import Path

import pytest

from mcp_test_harness.scaffold import run_init


def test_init_writes_test_and_config(tmp_path: Path) -> None:
    code = run_init(
        [
            "--dir",
            str(tmp_path),
            "--server-command",
            "python -c \"print(1)\"",
            "--filename",
            "test_x.py",
        ],
    )
    assert code == 0
    tf = tmp_path / "tests" / "test_x.py"
    assert tf.is_file()
    assert "mcp_server" in tf.read_text(encoding="utf-8")
    y = tmp_path / "mcp-test.yaml"
    assert y.is_file()
    txt = y.read_text(encoding="utf-8")
    assert "server:" in txt
    assert "print(1)" in txt


def test_init_refuse_overwrite(tmp_path: Path) -> None:
    (tmp_path / "tests").mkdir()
    f = tmp_path / "tests" / "t.py"
    f.write_text("#", encoding="utf-8")
    c = run_init(["--dir", str(tmp_path), "--filename", "t.py"])
    assert c == 2
    c2 = run_init(["--dir", str(tmp_path), "--filename", "t.py", "--force"])
    assert c2 == 0


def test_init_no_config_skips_yaml(tmp_path: Path) -> None:
    c = run_init(
        [
            "--dir",
            str(tmp_path),
            "--no-config",
            "--filename",
            "test_only.py",
        ],
    )
    assert c == 0
    assert (tmp_path / "tests" / "test_only.py").is_file()
    assert not (tmp_path / "mcp-test.yaml").exists()


def test_main_cli_dispatches_to_init(tmp_path: Path) -> None:
    from mcp_test_harness.cli import main

    code = main(
        [
            "init",
            "--dir",
            str(tmp_path),
            "--no-config",
            "--filename",
            "cli_init.py",
        ],
    )
    assert code == 0
    assert (tmp_path / "tests" / "cli_init.py").is_file()


def test_init_preserves_existing_yaml_without_force(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    ypath = tmp_path / "mcp-test.yaml"
    ypath.write_text("server:\n  command: keep-original\n", encoding="utf-8")
    c = run_init(["--dir", str(tmp_path), "--filename", "starter.py"])
    assert c == 0
    assert "keep-original" in ypath.read_text(encoding="utf-8")
    err = capsys.readouterr().err
    assert "Skipped mcp-test.yaml" in err
