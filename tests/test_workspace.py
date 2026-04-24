"""Smoke tests: workspace shim after editable install."""

from __future__ import annotations

import importlib.util

import pytest

from mcplint import bastion_version, bedrock_version


def test_bastion_version_pep440() -> None:
    if importlib.util.find_spec("mcp_bastion") is None:
        pytest.skip("mcp-bastion-python not installed (optional extra: mcp-test-harness[mcplint])")
    v = bastion_version()
    assert v and len(v) >= 3


def test_bedrock_optional() -> None:
    # May be None if extra not installed -- both outcomes are valid.
    bedrock_version()
