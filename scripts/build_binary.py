#!/usr/bin/env python3
"""Build the mcp-test standalone binary using PyInstaller.

This script invokes PyInstaller with the project spec file and places
the resulting binary in the ``dist/`` directory.

Usage:
    python scripts/build_binary.py            # default build
    python scripts/build_binary.py --clean    # clean build artifacts first

The actual cross-platform matrix (Linux x86_64/aarch64, macOS x86_64/aarch64,
Windows x86_64) is handled by CI runners -- this script just drives PyInstaller
on the current platform.

Requirements: 12.1, 12.2, 12.3
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC_FILE = ROOT / "mcp_test_harness.spec"
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build"


def clean() -> None:
    """Remove previous build artifacts."""
    for d in (DIST_DIR, BUILD_DIR):
        if d.exists():
            shutil.rmtree(d)
            print(f"Removed {d}")


def build() -> int:
    """Run PyInstaller with the spec file. Returns the process exit code."""
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        str(SPEC_FILE),
    ]
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(ROOT))
    return result.returncode


def verify() -> bool:
    """Quick smoke test: run ``mcp-test --version`` from the built binary."""
    suffix = ".exe" if sys.platform == "win32" else ""
    binary = DIST_DIR / f"mcp-test{suffix}"
    if not binary.exists():
        print(f"ERROR: Binary not found at {binary}")
        return False

    result = subprocess.run(
        [str(binary), "--version"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        print(f"ERROR: mcp-test --version exited with code {result.returncode}")
        print(result.stderr)
        return False

    print(f"OK: {result.stdout.strip()}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the mcp-test binary")
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove build/dist directories before building",
    )
    parser.add_argument(
        "--skip-verify",
        action="store_true",
        help="Skip the post-build smoke test",
    )
    args = parser.parse_args()

    if args.clean:
        clean()

    rc = build()
    if rc != 0:
        print(f"PyInstaller exited with code {rc}")
        return rc

    if not args.skip_verify:
        if not verify():
            return 1

    print("Build complete. Binary is at dist/mcp-test")
    return 0


if __name__ == "__main__":
    sys.exit(main())
