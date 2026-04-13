"""MCPLint -- workspace shim that pins MCP-Bastion so `pip install -e .` pulls it automatically."""

from __future__ import annotations

import importlib.metadata

__all__ = ["bastion_version", "bedrock_version"]


def bastion_version() -> str:
    """Return installed mcp-bastion-python version (PEP 440 string)."""
    return importlib.metadata.version("mcp-bastion-python")


def bedrock_version() -> str | None:
    """Return mcp-bastion-bedrock version if the optional extra is installed."""
    try:
        return importlib.metadata.version("mcp-bastion-bedrock")
    except importlib.metadata.PackageNotFoundError:
        return None
