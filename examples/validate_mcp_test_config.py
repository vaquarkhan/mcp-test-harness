#!/usr/bin/env python3
"""
Validate a mcp-test.yaml / mcp-test.toml file without running tests.

    python examples/validate_mcp_test_config.py
    python examples/validate_mcp_test_config.py path/to/mcp-test.yaml

Exit code 0 if there are no errors, 1 if validation errors were reported.

Prerequisites:
    pip install -e "."
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mcp_test_harness.config import validate_config_file


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "config",
        nargs="?",
        type=Path,
        help="Config file (default: ./mcp-test.yaml or ./mcp-test.toml in cwd, if present)",
    )
    args = p.parse_args()
    if args.config is not None:
        path = args.config
    else:
        for name in ("mcp-test.yaml", "mcp-test.yml", "mcp-test.toml"):
            c = Path(name)
            if c.is_file():
                path = c
                break
        else:
            # Fall back: validate sample next to this script (always valid)
            path = Path(__file__).resolve().parent / "sample_mcp_test.yaml"
    errs = validate_config_file(path)
    if not errs:
        print(f"OK: {path} - no known schema issues.")
        return 0
    print(f"Problems in {path}:", file=sys.stderr)
    for e in errs:
        line = f" (line {e.line})" if e.line else ""
        print(f"  - {e.message}{line}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
