#!/usr/bin/env python3
"""
Version gate -- fail fast if MCP-Bastion or the test harness is below a required minimum.

Useful in CI or startup scripts to enforce a minimum baseline.

Run:
    python examples/version_gate.py
"""

from __future__ import annotations

import sys
from packaging.version import Version

from mcplint import bastion_version
from mcp_test_harness import __version__ as harness_version


MINIMUM_BASTION = "1.0.12"
MINIMUM_HARNESS = "0.1.0"


def enforce_minimum_versions() -> None:
    """Exit non-zero if any package is below the required minimum."""
    errors = []

    # Check MCP-Bastion
    installed_bastion = bastion_version()
    if Version(installed_bastion) < Version(MINIMUM_BASTION):
        errors.append(
            f"mcp-bastion-python {installed_bastion} < {MINIMUM_BASTION}"
        )
    else:
        print(f"OK: mcp-bastion-python {installed_bastion} >= {MINIMUM_BASTION}")

    # Check test harness
    if Version(harness_version) < Version(MINIMUM_HARNESS):
        errors.append(
            f"mcp-test-harness {harness_version} < {MINIMUM_HARNESS}"
        )
    else:
        print(f"OK: mcp-test-harness {harness_version} >= {MINIMUM_HARNESS}")

    if errors:
        for err in errors:
            print(f"FAIL: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    enforce_minimum_versions()
