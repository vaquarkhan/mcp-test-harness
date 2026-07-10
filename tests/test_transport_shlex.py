"""Stdio command parsing uses ``split_server_command`` (quoted segments, spaces)."""

from __future__ import annotations

import os
from unittest.mock import patch

from mcp_test_harness.transport import split_server_command


def test_shlex_preserves_quoted_whitespace() -> None:
    cmd = 'myapp "one arg" second'
    parts = split_server_command(cmd)
    assert len(parts) < len(cmd.split())
    assert len(parts) == 3
    assert parts[0] == "myapp"
    assert parts[1] == "one arg"
    assert parts[2] == "second"


def test_windows_strips_quotes_around_paths_with_spaces() -> None:
    """BUG G: posix=False leaves literal quotes; we must strip them."""
    cmd = r'python "C:\Program Files\mcp\server.py"'
    with patch("mcp_test_harness.transport.os.name", "nt"):
        parts = split_server_command(cmd)
    assert parts[0] == "python"
    assert parts[1] == r"C:\Program Files\mcp\server.py"
    assert '"' not in parts[1]


def test_windows_strips_single_quotes() -> None:
    cmd = "python 'C:\\Users\\First Last\\server.py'"
    with patch("mcp_test_harness.transport.os.name", "nt"):
        parts = split_server_command(cmd)
    assert parts == ["python", r"C:\Users\First Last\server.py"]


def test_posix_keeps_normal_split() -> None:
    cmd = 'python "/tmp/my server.py"'
    with patch("mcp_test_harness.transport.os.name", "posix"):
        parts = split_server_command(cmd)
    assert parts == ["python", "/tmp/my server.py"]


def test_empty_command() -> None:
    assert split_server_command("") == []
    assert split_server_command("   ") == []
