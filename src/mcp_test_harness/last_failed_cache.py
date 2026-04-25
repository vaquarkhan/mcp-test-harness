"""Persistence for ``mcp-test --last-failed`` (pytest-style re-run)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mcp_test_harness.discovery import HarnessCase
from mcp_test_harness.models import CaseStatus, SessionResults

_CACHE_DIR = ".mcp_test_harness"
_FILE = "last-failed.json"


def last_failed_path(cwd: Path | None = None) -> Path:
    base = cwd or Path.cwd()
    return (base / _CACHE_DIR / _FILE).resolve()


def _normalize_module(s: str) -> str:
    return Path(s).as_posix()


def write_last_failed_keys(keys: list[tuple[str, str]], cwd: Path | None = None) -> None:
    """Write failed (module, name) pairs. Empty *keys* removes the cache file."""
    path = last_failed_path(cwd)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not keys:
        if path.is_file():
            path.unlink()
        return
    payload = {
        "version": 1,
        "failed": [{"module": _normalize_module(m), "name": n} for m, n in keys],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def read_last_failed_keys(cwd: Path | None = None) -> list[tuple[str, str]]:
    """Return stored (module, name) pairs, or empty list if missing/invalid."""
    path = last_failed_path(cwd)
    if not path.is_file():
        return []
    try:
        data: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, dict):
        return []
    raw = data.get("failed")
    if not isinstance(raw, list):
        return []
    out: list[tuple[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        m = item.get("module")
        n = item.get("name")
        if isinstance(m, str) and isinstance(n, str):
            out.append((_normalize_module(m), n))
    return out


def keys_from_session_results(results: SessionResults) -> list[tuple[str, str]]:
    """(module path posix, name) for failed, errored, and timed out tests (for the cache)."""
    out: list[tuple[str, str]] = []
    for r in results.test_results:
        if r.status not in (CaseStatus.FAILED, CaseStatus.ERROR, CaseStatus.TIMEOUT):
            continue
        mod = (r.file or r.module or "").strip()
        if not mod:
            continue
        out.append((Path(mod).as_posix(), r.name))
    return out


def filter_harness_cases(cases: list[HarnessCase], keys: list[tuple[str, str]]) -> list[HarnessCase]:
    """Return only cases whose (module, name) pair appears in *keys*.

    If *keys* is empty, returns an empty list (``--last-failed`` with no cache / no
    previous failures).
    """
    if not keys:
        return []
    kset = {(Path(m).as_posix(), n) for m, n in keys}
    out: list[HarnessCase] = []
    for tc in cases:
        key = (Path(tc.module_path).as_posix(), tc.name)
        if key in kset:
            out.append(tc)
    return out
