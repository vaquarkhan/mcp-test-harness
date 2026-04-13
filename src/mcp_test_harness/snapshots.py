"""Snapshot manager for MCP response snapshot testing."""

from __future__ import annotations

import json
import difflib
from pathlib import Path
from typing import Any


class SnapshotManager:
    """Manages snapshot files for snapshot testing.

    Snapshots are stored as JSON files in a ``__snapshots__`` directory
    adjacent to the test file.
    """

    def __init__(self, *, update: bool = False) -> None:
        self._update = update

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------

    def get_snapshot_path(self, test_file: Path, test_name: str) -> Path:
        """Return ``<test_dir>/__snapshots__/<test_name>.snap``."""
        return test_file.parent / "__snapshots__" / f"{test_name}.snap"

    # ------------------------------------------------------------------
    # Read / write
    # ------------------------------------------------------------------

    def read_snapshot(self, path: Path) -> Any | None:
        """Read a stored snapshot.  Returns ``None`` when the file is missing."""
        if not path.exists():
            return None
        text = path.read_text(encoding="utf-8")
        return json.loads(text)

    def write_snapshot(self, path: Path, data: Any) -> None:
        """Write *data* as a JSON snapshot file, creating directories as needed."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # Diff
    # ------------------------------------------------------------------

    def diff(self, expected: Any, actual: Any) -> str:
        """Produce a unified-diff string between *expected* and *actual*.

        Both values are serialised to pretty-printed JSON before diffing so
        the output is human-readable.
        """
        expected_lines = _to_json_lines(expected)
        actual_lines = _to_json_lines(actual)
        diff_lines = difflib.unified_diff(
            expected_lines,
            actual_lines,
            fromfile="expected (snapshot)",
            tofile="actual",
            lineterm="",
        )
        return "\n".join(diff_lines)

    # ------------------------------------------------------------------
    # High-level assert helper
    # ------------------------------------------------------------------

    def assert_match(
        self,
        actual: Any,
        test_file: Path,
        test_name: str,
    ) -> None:
        """Compare *actual* against the stored snapshot.

        * Creates the snapshot when it does not exist yet.
        * In update mode (``--update-snapshots``) overwrites unconditionally.
        """
        snap_path = self.get_snapshot_path(test_file, test_name)
        stored = self.read_snapshot(snap_path)

        if stored is None or self._update:
            self.write_snapshot(snap_path, actual)
            return

        if _normalise(stored) != _normalise(actual):
            diff_text = self.diff(stored, actual)
            raise AssertionError(
                f"Snapshot mismatch for {test_name}:\n{diff_text}"
            )


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------

def _to_json_lines(value: Any) -> list[str]:
    """Serialise *value* to sorted, indented JSON and split into lines."""
    return json.dumps(value, indent=2, sort_keys=True, default=str).splitlines()


def _normalise(value: Any) -> str:
    """Canonical JSON representation for equality comparison."""
    return json.dumps(value, sort_keys=True, default=str)
