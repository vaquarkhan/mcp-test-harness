"""Stdio command parsing uses ``shlex.split`` (quoted segments, spaces)."""

from __future__ import annotations

import os
import shlex


def test_shlex_preserves_quoted_whitespace() -> None:
    """Mirrors ``StdioTransportAdapter.connect``: posix=True on Unix, False on Windows."""
    cmd = 'myapp "one arg" second'
    parts = shlex.split(cmd, posix=os.name != "nt")
    # Quoted run must be fewer tokens than naive split (grouped segment).
    assert len(parts) < len(cmd.split())
    assert len(parts) == 3
    assert parts[0] == "myapp"
    assert "one arg" in parts[1].replace('"', "")
    assert parts[2] == "second"
