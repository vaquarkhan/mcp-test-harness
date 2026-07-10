"""Console I/O helpers — make CLI output safe on Windows cp1252 consoles."""

from __future__ import annotations

import sys


def configure_stdio() -> None:
    """Prefer UTF-8 on stdout/stderr so em-dashes and arrows do not crash Windows.

    Safe to call multiple times. No-op when streams lack ``reconfigure`` (e.g. some
    redirected/mocked streams in tests).
    """
    for stream in (sys.stdout, sys.stderr):
        reconf = getattr(stream, "reconfigure", None)
        if callable(reconf):
            try:
                reconf(encoding="utf-8", errors="replace")
            except Exception:  # noqa: BLE001 — best-effort only
                pass
