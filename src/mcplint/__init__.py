"""MCP Test Harness — workspace shim (optional MCP-Bastion pin)."""

from __future__ import annotations

import importlib.metadata

__all__ = ["bastion_version", "bedrock_version"]


def bastion_version() -> str:
    """Return installed ``mcp-bastion-python`` version, or raise if not installed.

    Install the optional extra: ``pip install mcp-test-harness[mcplint]``.
    """
    try:
        return importlib.metadata.version("mcp-bastion-python")
    except importlib.metadata.PackageNotFoundError as exc:  # pragma: no cover
        msg = (
            "mcp-bastion-python is not installed. Install the optional mcplint extra: "
            "pip install mcp-test-harness[mcplint]"
        )
        raise RuntimeError(msg) from exc


def bedrock_version() -> str | None:
    """Return mcp-bastion-bedrock version if the optional extra is installed."""
    try:
        return importlib.metadata.version("mcp-bastion-bedrock")
    except importlib.metadata.PackageNotFoundError:
        return None
