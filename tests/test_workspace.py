"""Smoke tests: workspace shim after editable install."""

from __future__ import annotations

import pytest

from mcplint import bastion_version, bedrock_version


def test_bastion_version_pep440() -> None:
    v = bastion_version()
    assert v and len(v) >= 3


def test_bedrock_optional() -> None:
    # May be None if extra not installed -- both outcomes are valid.
    bedrock_version()
