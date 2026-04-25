"""Unit tests for .mcp_test_harness/last-failed cache helpers."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from mcp_test_harness.discovery import HarnessCase
from mcp_test_harness.last_failed_cache import (
    filter_harness_cases,
    keys_from_session_results,
    last_failed_path,
    read_last_failed_keys,
    write_last_failed_keys,
)
from mcp_test_harness.models import CaseResult, CaseStatus, SessionResults


def _case(name: str, mod: str) -> HarnessCase:
    async def _fn() -> None:
        pass

    return HarnessCase(name=name, module_path=Path(mod), func=_fn, is_async=True)


def test_write_read_roundtrip(tmp_path: Path) -> None:
    p = last_failed_path(tmp_path)
    assert p == tmp_path / ".mcp_test_harness" / "last-failed.json"
    write_last_failed_keys([("a/b.py", "t1")], cwd=tmp_path)
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["version"] == 1
    assert data["failed"] == [{"module": "a/b.py", "name": "t1"}]
    assert read_last_failed_keys(cwd=tmp_path) == [("a/b.py", "t1")]


def test_write_empty_unlinks(tmp_path: Path) -> None:
    write_last_failed_keys([("m.py", "t")], cwd=tmp_path)
    write_last_failed_keys([], cwd=tmp_path)
    assert not last_failed_path(tmp_path).is_file()


def test_read_invalid_is_empty(tmp_path: Path) -> None:
    p = last_failed_path(tmp_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("not json", encoding="utf-8")
    assert read_last_failed_keys(cwd=tmp_path) == []


def test_read_text_oserror(tmp_path: Path) -> None:
    p = last_failed_path(tmp_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("{}", encoding="utf-8")
    with patch.object(Path, "read_text", side_effect=OSError("denied")):
        assert read_last_failed_keys(cwd=tmp_path) == []


def test_read_not_dict_top_level(tmp_path: Path) -> None:
    p = last_failed_path(tmp_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("[]", encoding="utf-8")
    assert read_last_failed_keys(cwd=tmp_path) == []


def test_read_failed_not_list(tmp_path: Path) -> None:
    p = last_failed_path(tmp_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text('{"version":1,"failed":{}}', encoding="utf-8")
    assert read_last_failed_keys(cwd=tmp_path) == []


def test_read_skips_bad_items(tmp_path: Path) -> None:
    p = last_failed_path(tmp_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        '{"version":1,"failed":["nope",{"module":"m.py","name":"t"}]}',
        encoding="utf-8",
    )
    assert read_last_failed_keys(cwd=tmp_path) == [(Path("m.py").as_posix(), "t")]


def test_keys_skips_empty_module() -> None:
    sr = SessionResults(
        test_results=[
            CaseResult("x", "", CaseStatus.FAILED, 1.0, file=""),
        ],
        total_duration_ms=1.0,
        server_capabilities={},
        protocol_version="",
        harness_version="1.1.0",
    )
    assert keys_from_session_results(sr) == []


def test_filter_harness_cases_empty_keys() -> None:
    c = _case("t", "m.py")
    assert filter_harness_cases([c], []) == []


def test_filter_harness_cases_matches() -> None:
    c1 = _case("t1", "m.py")
    c2 = _case("t2", "m.py")
    out = filter_harness_cases(
        [c1, c2], [(Path("m.py").as_posix(), "t1")]
    )
    assert [x.name for x in out] == ["t1"]


def test_keys_from_session_results() -> None:
    sr = SessionResults(
        test_results=[
            CaseResult("a", "m", CaseStatus.PASSED, 1.0, file="x.py"),
            CaseResult("b", "m", CaseStatus.FAILED, 1.0, file="y.py"),
        ],
        total_duration_ms=1.0,
        server_capabilities={},
        protocol_version="",
        harness_version="1.1.0",
        passed=0,
        failed=0,
        errored=0,
        skipped=0,
        timed_out=0,
    )
    assert keys_from_session_results(sr) == [(Path("y.py").as_posix(), "b")]
