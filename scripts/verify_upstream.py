#!/usr/bin/env python3
"""End-to-end smoke check: upstream packages import after automatic install."""

from __future__ import annotations

import sys


def main() -> int:
    try:
        import mcp_bastion  # noqa: F401
    except ImportError as e:
        print("FAIL: mcp_bastion import:", e, file=sys.stderr)
        return 1

    from mcplint import bastion_version, bedrock_version

    print("OK  mcp-bastion-python", bastion_version())
    bv = bedrock_version()
    if bv:
        print("OK  mcp-bastion-bedrock", bv)
    else:
        print("SKIP mcp-bastion-bedrock (install extra: pip install -e .[bedrock])")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
