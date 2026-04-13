"""Tests for mcp_test_harness.discovery module."""

from __future__ import annotations

from pathlib import Path

from mcp_test_harness.discovery import (
    HarnessCase,
    HarnessModule,
    _MARKER_ATTR,
    discover_tests,
    marker,
    skip,
)


# ---------------------------------------------------------------------------
# marker / skip decorators
# ---------------------------------------------------------------------------


class TestMarkerDecorator:
    def test_timeout(self) -> None:
        @marker(timeout=5)
        def test_fn() -> None: ...

        assert getattr(test_fn, _MARKER_ATTR) == {"timeout": 5}

    def test_retry(self) -> None:
        @marker(retry=3)
        def test_fn() -> None: ...

        assert getattr(test_fn, _MARKER_ATTR) == {"retry": 3}

    def test_tags(self) -> None:
        @marker(tags=["slow", "network"])
        def test_fn() -> None: ...

        markers = getattr(test_fn, _MARKER_ATTR)
        assert set(markers["tags"]) == {"slow", "network"}

    def test_combined(self) -> None:
        @marker(timeout=10, retry=2, tags=["ci"])
        def test_fn() -> None: ...

        m = getattr(test_fn, _MARKER_ATTR)
        assert m["timeout"] == 10
        assert m["retry"] == 2
        assert "ci" in m["tags"]

    def test_skip_via_marker(self) -> None:
        @marker(skip=True, reason="not ready")
        def test_fn() -> None: ...

        m = getattr(test_fn, _MARKER_ATTR)
        assert m["skip"] is True
        assert m["reason"] == "not ready"

    def test_stacking(self) -> None:
        @marker(timeout=5)
        @marker(tags=["fast"])
        def test_fn() -> None: ...

        m = getattr(test_fn, _MARKER_ATTR)
        assert m["timeout"] == 5
        assert "fast" in m["tags"]


class TestSkipDecorator:
    def test_bare_skip(self) -> None:
        @skip
        def test_fn() -> None: ...

        assert getattr(test_fn, _MARKER_ATTR)["skip"] is True

    def test_skip_with_reason(self) -> None:
        @skip(reason="bug #42")
        def test_fn() -> None: ...

        m = getattr(test_fn, _MARKER_ATTR)
        assert m["skip"] is True
        assert m["reason"] == "bug #42"


# ---------------------------------------------------------------------------
# File pattern matching
# ---------------------------------------------------------------------------


class TestFileDiscovery:
    def test_discovers_test_prefix(self, tmp_path: Path) -> None:
        f = tmp_path / "test_example.py"
        f.write_text("def test_one(): pass\n")
        modules = discover_tests([tmp_path])
        assert len(modules) == 1
        assert modules[0].test_cases[0].name == "test_one"

    def test_discovers_test_suffix(self, tmp_path: Path) -> None:
        f = tmp_path / "example_test.py"
        f.write_text("def test_two(): pass\n")
        modules = discover_tests([tmp_path])
        assert len(modules) == 1
        assert modules[0].test_cases[0].name == "test_two"

    def test_ignores_non_test_files(self, tmp_path: Path) -> None:
        (tmp_path / "helper.py").write_text("def test_nope(): pass\n")
        modules = discover_tests([tmp_path])
        assert modules == []

    def test_recursive_search(self, tmp_path: Path) -> None:
        sub = tmp_path / "sub" / "deep"
        sub.mkdir(parents=True)
        (sub / "test_deep.py").write_text("def test_deep(): pass\n")
        modules = discover_tests([tmp_path])
        assert len(modules) == 1
        assert modules[0].test_cases[0].name == "test_deep"

    def test_single_file_path(self, tmp_path: Path) -> None:
        f = tmp_path / "test_single.py"
        f.write_text("def test_a(): pass\ndef test_b(): pass\n")
        modules = discover_tests([f])
        assert len(modules) == 1
        assert len(modules[0].test_cases) == 2


# ---------------------------------------------------------------------------
# Function and class extraction
# ---------------------------------------------------------------------------


class TestExtraction:
    def test_extracts_functions(self, tmp_path: Path) -> None:
        f = tmp_path / "test_funcs.py"
        f.write_text("def test_alpha(): pass\ndef test_beta(): pass\ndef helper(): pass\n")
        modules = discover_tests([tmp_path])
        names = [tc.name for tc in modules[0].test_cases]
        assert "test_alpha" in names
        assert "test_beta" in names
        assert "helper" not in names

    def test_extracts_class_methods(self, tmp_path: Path) -> None:
        f = tmp_path / "test_cls.py"
        f.write_text(
            "class TestFoo:\n"
            "    def test_method(self): pass\n"
            "    def helper(self): pass\n"
        )
        modules = discover_tests([tmp_path])
        names = [tc.name for tc in modules[0].test_cases]
        assert "TestFoo.test_method" in names
        assert len(names) == 1

    def test_ignores_non_test_classes(self, tmp_path: Path) -> None:
        f = tmp_path / "test_ignore.py"
        f.write_text("class Helper:\n    def test_nope(self): pass\n")
        modules = discover_tests([tmp_path])
        assert modules == []


# ---------------------------------------------------------------------------
# Async detection
# ---------------------------------------------------------------------------


class TestAsyncDetection:
    def test_sync_function(self, tmp_path: Path) -> None:
        f = tmp_path / "test_sync.py"
        f.write_text("def test_sync(): pass\n")
        modules = discover_tests([tmp_path])
        assert modules[0].test_cases[0].is_async is False

    def test_async_function(self, tmp_path: Path) -> None:
        f = tmp_path / "test_async.py"
        f.write_text("async def test_async(): pass\n")
        modules = discover_tests([tmp_path])
        assert modules[0].test_cases[0].is_async is True


# ---------------------------------------------------------------------------
# Marker parsing from decorators
# ---------------------------------------------------------------------------


class TestMarkerParsing:
    def test_markers_from_decorator(self, tmp_path: Path) -> None:
        f = tmp_path / "test_marked.py"
        f.write_text(
            "from mcp_test_harness.discovery import marker\n"
            "\n"
            "@marker(timeout=15, tags=['slow'])\n"
            "def test_slow(): pass\n"
        )
        modules = discover_tests([tmp_path])
        tc = modules[0].test_cases[0]
        assert tc.markers["timeout"] == 15
        assert "slow" in tc.markers["tags"]

    def test_skip_marker_detected(self, tmp_path: Path) -> None:
        f = tmp_path / "test_skipped.py"
        f.write_text(
            "from mcp_test_harness.discovery import skip\n"
            "\n"
            "@skip\n"
            "def test_skipped(): pass\n"
        )
        modules = discover_tests([tmp_path])
        tc = modules[0].test_cases[0]
        assert tc.markers.get("skip") is True


# ---------------------------------------------------------------------------
# -k name filter
# ---------------------------------------------------------------------------


class TestNameFilter:
    def test_substring_match(self, tmp_path: Path) -> None:
        f = tmp_path / "test_filter.py"
        f.write_text("def test_alpha(): pass\ndef test_beta(): pass\n")
        modules = discover_tests([tmp_path], filter_name="alpha")
        names = [tc.name for tc in modules[0].test_cases]
        assert names == ["test_alpha"]

    def test_glob_match(self, tmp_path: Path) -> None:
        f = tmp_path / "test_filter.py"
        f.write_text("def test_alpha(): pass\ndef test_beta(): pass\n")
        modules = discover_tests([tmp_path], filter_name="*beta*")
        names = [tc.name for tc in modules[0].test_cases]
        assert names == ["test_beta"]

    def test_case_insensitive(self, tmp_path: Path) -> None:
        f = tmp_path / "test_filter.py"
        f.write_text("def test_Alpha(): pass\n")
        modules = discover_tests([tmp_path], filter_name="alpha")
        assert len(modules[0].test_cases) == 1

    def test_no_match_excludes_module(self, tmp_path: Path) -> None:
        f = tmp_path / "test_filter.py"
        f.write_text("def test_alpha(): pass\n")
        modules = discover_tests([tmp_path], filter_name="zzz")
        assert modules == []


# ---------------------------------------------------------------------------
# -m marker filter
# ---------------------------------------------------------------------------


class TestMarkerFilter:
    def test_filter_by_marker_key(self, tmp_path: Path) -> None:
        f = tmp_path / "test_mf.py"
        f.write_text(
            "from mcp_test_harness.discovery import marker, skip\n"
            "\n"
            "@skip\n"
            "def test_skipped(): pass\n"
            "\n"
            "def test_normal(): pass\n"
        )
        modules = discover_tests([tmp_path], filter_marker="skip")
        names = [tc.name for tc in modules[0].test_cases]
        assert names == ["test_skipped"]

    def test_filter_by_tag(self, tmp_path: Path) -> None:
        f = tmp_path / "test_mf.py"
        f.write_text(
            "from mcp_test_harness.discovery import marker\n"
            "\n"
            "@marker(tags=['slow'])\n"
            "def test_slow(): pass\n"
            "\n"
            "def test_fast(): pass\n"
        )
        modules = discover_tests([tmp_path], filter_marker="slow")
        names = [tc.name for tc in modules[0].test_cases]
        assert names == ["test_slow"]

    def test_no_marker_match_excludes_module(self, tmp_path: Path) -> None:
        f = tmp_path / "test_mf.py"
        f.write_text("def test_plain(): pass\n")
        modules = discover_tests([tmp_path], filter_marker="slow")
        assert modules == []
