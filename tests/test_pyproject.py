"""Offline checks: dependency pin exists without importing MCP-Bastion (large transitive deps)."""

from __future__ import annotations

from pathlib import Path


def test_pyproject_pins_mcp_bastion_python() -> None:
    root = Path(__file__).resolve().parents[1]
    text = (root / "pyproject.toml").read_text(encoding="utf-8")
    assert "mcp-bastion-python>=" in text.replace(" ", "")
