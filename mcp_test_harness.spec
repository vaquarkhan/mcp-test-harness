# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for the mcp-test standalone binary.

Bundles the mcp_test_harness package, Python interpreter, and all
dependencies into a single `mcp-test` executable.

Supported platforms (built via CI with platform-specific runners):
  - Linux x86_64, aarch64
  - macOS x86_64, aarch64 (universal2)
  - Windows x86_64

Usage:
  pyinstaller mcp_test_harness.spec

Requirements: 12.1, 12.2, 12.3, 12.5
"""

import sys
from pathlib import Path

block_cipher = None

# Collect all mcp_test_harness submodules so nothing is missed at runtime.
hiddenimports = [
    "mcp_test_harness",
    "mcp_test_harness.assertions",
    "mcp_test_harness.cli",
    "mcp_test_harness.config",
    "mcp_test_harness.discovery",
    "mcp_test_harness.executor",
    "mcp_test_harness.fixtures",
    "mcp_test_harness.lifecycle",
    "mcp_test_harness.models",
    "mcp_test_harness.parser",
    "mcp_test_harness.plugins",
    "mcp_test_harness.reporting",
    "mcp_test_harness.scheduler",
    "mcp_test_harness.schema",
    "mcp_test_harness.snapshots",
    "mcp_test_harness.transport",
    # Third-party dependencies that PyInstaller may not auto-detect
    "yaml",
    "anyio",
    "anyio._backends._asyncio",
    "mcp",
    "jsonschema",
]

a = Analysis(
    ["src/mcp_test_harness/cli.py"],
    pathex=["src"],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "numpy",
        "scipy",
        "PIL",
        "IPython",
        "notebook",
    ],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="mcp-test",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,  # Use native arch; CI sets this per runner
    codesign_identity=None,
    entitlements_file=None,
)
