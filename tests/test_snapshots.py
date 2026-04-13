"""Tests for mcp_test_harness.snapshots -- SnapshotManager."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mcp_test_harness.snapshots import SnapshotManager


class TestGetSnapshotPath:
    def test_path_convention(self, tmp_path: Path):
        mgr = SnapshotManager()
        test_file = tmp_path / "test_example.py"
        path = mgr.get_snapshot_path(test_file, "my_snap")
        assert path == tmp_path / "__snapshots__" / "my_snap.snap"


class TestReadSnapshot:
    def test_returns_none_when_missing(self, tmp_path: Path):
        mgr = SnapshotManager()
        assert mgr.read_snapshot(tmp_path / "nope.snap") is None

    def test_reads_json(self, tmp_path: Path):
        snap = tmp_path / "data.snap"
        snap.write_text('{"key": "value"}\n')
        mgr = SnapshotManager()
        data = mgr.read_snapshot(snap)
        assert data == {"key": "value"}


class TestWriteSnapshot:
    def test_creates_directories(self, tmp_path: Path):
        mgr = SnapshotManager()
        snap = tmp_path / "sub" / "deep" / "snap.snap"
        mgr.write_snapshot(snap, {"a": 1})
        assert snap.exists()
        assert json.loads(snap.read_text()) == {"a": 1}


class TestDiff:
    def test_produces_unified_diff(self):
        mgr = SnapshotManager()
        diff = mgr.diff({"a": 1}, {"a": 2})
        assert "---" in diff
        assert "+++" in diff
        assert "-  \"a\": 1" in diff or '- "a": 1' in diff.replace("  ", " ")

    def test_identical_produces_empty_diff(self):
        mgr = SnapshotManager()
        diff = mgr.diff({"a": 1}, {"a": 1})
        assert diff == ""


class TestAssertMatch:
    def test_creates_snapshot_when_missing(self, tmp_path: Path):
        mgr = SnapshotManager()
        test_file = tmp_path / "test_x.py"
        test_file.touch()
        mgr.assert_match({"key": "val"}, test_file, "new_snap")
        snap = tmp_path / "__snapshots__" / "new_snap.snap"
        assert snap.exists()

    def test_passes_when_matches(self, tmp_path: Path):
        mgr = SnapshotManager()
        test_file = tmp_path / "test_x.py"
        test_file.touch()
        snap_dir = tmp_path / "__snapshots__"
        snap_dir.mkdir()
        snap = snap_dir / "match.snap"
        snap.write_text(json.dumps({"a": 1}, indent=2, sort_keys=True) + "\n")
        mgr.assert_match({"a": 1}, test_file, "match")

    def test_fails_on_mismatch(self, tmp_path: Path):
        mgr = SnapshotManager()
        test_file = tmp_path / "test_x.py"
        test_file.touch()
        snap_dir = tmp_path / "__snapshots__"
        snap_dir.mkdir()
        snap = snap_dir / "mm.snap"
        snap.write_text(json.dumps({"a": 1}, indent=2, sort_keys=True) + "\n")
        with pytest.raises(AssertionError, match="Snapshot mismatch"):
            mgr.assert_match({"a": 2}, test_file, "mm")

    def test_update_mode_overwrites(self, tmp_path: Path):
        mgr = SnapshotManager(update=True)
        test_file = tmp_path / "test_x.py"
        test_file.touch()
        snap_dir = tmp_path / "__snapshots__"
        snap_dir.mkdir()
        snap = snap_dir / "upd.snap"
        snap.write_text(json.dumps({"old": True}, indent=2, sort_keys=True) + "\n")
        mgr.assert_match({"new": True}, test_file, "upd")
        data = json.loads(snap.read_text())
        assert data == {"new": True}
