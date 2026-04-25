"""Test discovery for the MCP Test Harness.

Discovers test cases from the filesystem following pytest conventions:
- Files matching ``test_*.py`` or ``*_test.py``
- Functions prefixed with ``test_``
- Classes prefixed with ``Test``

Supports ``-k`` name pattern filtering, ``-m`` marker filtering,
async function detection, and marker parsing from decorators.
"""

from __future__ import annotations

import fnmatch
import importlib.util
import inspect
import logging
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Marker decorator
# ---------------------------------------------------------------------------

_MARKER_ATTR = "_mcp_markers"


def marker(
    *,
    timeout: float | None = None,
    retry: int | None = None,
    tags: list[str] | None = None,
    skip: bool = False,
    reason: str | None = None,
    **kwargs: Any,
) -> Callable[[Callable], Callable]:
    """Attach test markers (timeout, retry, tags, skip, order, ...) to a test function.

    Usage::

        from mcp_test_harness import marker

        @marker(timeout=10, retry=3, tags=["slow"])
        async def test_something(mcp_server):
            ...

        @marker(order=1)
        async def test_first(mcp_server):
            ...
    """

    def decorator(func: Callable) -> Callable:
        markers: dict[str, Any] = getattr(func, _MARKER_ATTR, {})
        if timeout is not None:
            markers["timeout"] = timeout
        if retry is not None:
            markers["retry"] = retry
        if tags is not None:
            markers.setdefault("tags", [])
            markers["tags"] = list({*markers["tags"], *tags})
        if skip:
            markers["skip"] = True
        if reason is not None:
            markers["reason"] = reason
        # Store any extra keyword arguments (e.g. order)
        for key, value in kwargs.items():
            markers[key] = value
        setattr(func, _MARKER_ATTR, markers)
        return func

    return decorator


def skip(func: Callable | None = None, *, reason: str | None = None) -> Any:
    """Mark a test to be skipped.

    Can be used as a bare decorator or with a reason::

        @skip
        def test_not_ready(): ...

        @skip(reason="server bug #42")
        def test_broken(): ...
    """
    if func is not None:
        # Used as @skip (no parentheses)
        markers: dict[str, Any] = getattr(func, _MARKER_ATTR, {})
        markers["skip"] = True
        setattr(func, _MARKER_ATTR, markers)
        return func

    # Used as @skip(reason="...")
    return marker(skip=True, reason=reason)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class HarnessCase:
    """A single discovered test case."""

    name: str
    module_path: Path
    func: Callable
    markers: dict[str, Any] = field(default_factory=dict)
    is_async: bool = False


@dataclass
class HarnessModule:
    """A discovered test module containing test cases."""

    path: Path
    test_cases: list[HarnessCase] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_TEST_FILE_PATTERNS = ("test_*.py", "*_test.py")


def _is_test_file(path: Path) -> bool:
    """Return True if *path* matches a test file naming convention."""
    name = path.name
    return any(fnmatch.fnmatch(name, pat) for pat in _TEST_FILE_PATTERNS)


def _get_markers(obj: Any) -> dict[str, Any]:
    """Extract ``_mcp_markers`` from a callable, if present."""
    return dict(getattr(obj, _MARKER_ATTR, {}))


def _extract_test_cases(module: Any, module_path: Path) -> list[HarnessCase]:
    """Extract ``test_`` functions and methods from ``Test`` classes."""
    cases: list[HarnessCase] = []

    for attr_name in sorted(dir(module)):
        obj = getattr(module, attr_name, None)
        if obj is None:
            continue

        # Top-level test functions
        if attr_name.startswith("test_") and (
            inspect.isfunction(obj) or inspect.iscoroutinefunction(obj)
        ):
            if inspect.isgeneratorfunction(obj) or inspect.isasyncgenfunction(obj):
                logger.warning(
                    "Skipping generator test %s in %s: test functions cannot be generators",
                    attr_name,
                    module_path,
                )
                continue
            cases.append(
                HarnessCase(
                    name=attr_name,
                    module_path=module_path,
                    func=obj,
                    markers=_get_markers(obj),
                    is_async=inspect.iscoroutinefunction(obj),
                )
            )
            continue

        # Test classes
        if attr_name.startswith("Test") and inspect.isclass(obj):
            for method_name in sorted(dir(obj)):
                if not method_name.startswith("test_"):
                    continue
                method = getattr(obj, method_name, None)
                if method is None:
                    continue
                if not (inspect.isfunction(method) or inspect.iscoroutinefunction(method)):
                    continue
                if inspect.isgeneratorfunction(method) or inspect.isasyncgenfunction(method):
                    logger.warning(
                        "Skipping generator test %s.%s in %s: test functions cannot be generators",
                        attr_name,
                        method_name,
                        module_path,
                    )
                    continue
                cases.append(
                    HarnessCase(
                        name=f"{attr_name}.{method_name}",
                        module_path=module_path,
                        func=method,
                        markers=_get_markers(method),
                        is_async=inspect.iscoroutinefunction(method),
                    )
                )

    return cases


def _load_module_from_path(path: Path) -> Any:
    """Dynamically import a Python module from a file path."""
    module_name = f"_mcp_discovered_{path.stem}_{id(path)}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        logger.warning(
            "Could not build import spec for test file %s (skipping this path)",
            path,
        )
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        # Use error level so default CLI log settings (warning+) always show
        # why a file produced no tests, not only in --verbose.
        logger.error(
            "Failed to import test module %s: %s",
            path,
            exc,
            exc_info=True,
        )
        sys.modules.pop(module_name, None)
        return None
    return module


def _matches_name_filter(name: str, pattern: str) -> bool:
    """Check if *name* matches a ``-k`` style filter pattern.

    Supports simple substring matching and ``*`` / ``?`` glob characters.
    """
    # If the pattern contains glob chars, use fnmatch; otherwise substring.
    if "*" in pattern or "?" in pattern:
        return fnmatch.fnmatch(name, f"*{pattern}*")
    return pattern.lower() in name.lower()


def _matches_marker_filter(markers: dict[str, Any], filter_marker: str) -> bool:
    """Check if *markers* satisfy a ``-m`` marker filter.

    The filter is a marker key name (e.g. ``"slow"``).  A test matches if:
    - The marker key exists directly (e.g. ``skip``, ``timeout``), OR
    - The marker value appears in the ``tags`` list.
    """
    if filter_marker in markers:
        return True
    tags: list[str] = markers.get("tags", [])
    return filter_marker in tags


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def discover_tests(
    paths: list[Path],
    filter_name: str | None = None,
    filter_marker: str | None = None,
) -> list[HarnessModule]:
    """Recursively discover test modules and extract test cases.

    Parameters
    ----------
    paths:
        Directories or files to search.
    filter_name:
        ``-k`` style name pattern filter (substring or glob).
    filter_marker:
        ``-m`` style marker filter (marker key or tag name).

    Returns
    -------
    list[HarnessModule]
        Discovered modules with their test cases.
    """
    test_files: list[Path] = []

    for p in paths:
        p = Path(p)
        if p.is_file() and _is_test_file(p):
            test_files.append(p)
        elif p.is_dir():
            for child in sorted(p.rglob("*.py")):
                if _is_test_file(child):
                    test_files.append(child)

    modules: list[HarnessModule] = []

    for file_path in test_files:
        mod = _load_module_from_path(file_path)
        if mod is None:
            continue

        cases = _extract_test_cases(mod, file_path)

        # Apply filters
        if filter_name is not None:
            cases = [c for c in cases if _matches_name_filter(c.name, filter_name)]
        if filter_marker is not None:
            cases = [
                c for c in cases if _matches_marker_filter(c.markers, filter_marker)
            ]

        if cases:
            modules.append(HarnessModule(path=file_path, test_cases=cases))

    return modules
