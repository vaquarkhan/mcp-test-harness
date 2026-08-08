"""Offline checks: dependency pin exists without importing MCP-Bastion (large transitive deps)."""

from __future__ import annotations

from pathlib import Path


def test_pyproject_pins_mcp_bastion_python() -> None:
    root = Path(__file__).resolve().parents[1]
    text = (root / "pyproject.toml").read_text(encoding="utf-8")
    assert "mcp-bastion-python>=" in text.replace(" ", "")
    # Bastion stays in [mcplint]; [dev] stays lightweight (no torch/spacy tree)
    assert 'mcplint = [\n  "mcp-bastion-python>=1.0.12",\n]' in text
    dev_block = text.split("dev = [")[1].split("]")[0]
    assert "mcp-bastion-python" not in dev_block


def test_pytest_testpaths_excludes_examples() -> None:
    root = Path(__file__).resolve().parents[1]
    text = (root / "pyproject.toml").read_text(encoding="utf-8")
    assert 'testpaths = ["tests"]' in text


def test_changelog_and_contributing_exist_and_are_in_sdist() -> None:
    root = Path(__file__).resolve().parents[1]
    toml = (root / "pyproject.toml").read_text(encoding="utf-8")
    for name in ("CHANGELOG.md", "CONTRIBUTING.md"):
        assert (root / name).is_file()
        assert f'  "{name}"' in toml, f"sdist should include {name}"
