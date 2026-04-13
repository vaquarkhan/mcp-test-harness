"""Tests for the plugin registry (mcp_test_harness.plugins).

Requirements: 9.1, 9.2, 9.3, 9.4, 9.5
"""

from __future__ import annotations

import types
from dataclasses import dataclass
from unittest.mock import patch

import pytest

from mcp_test_harness.fixtures import FixtureScope
from mcp_test_harness.plugins import (
    DiscoveryHook,
    MCPTestPlugin,
    PluginContext,
    PluginRegistry,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(plugins: list[str] | None = None):
    """Return a minimal config-like object with a ``plugins`` attribute."""

    @dataclass
    class _FakeConfig:
        plugins: list[str] | None = None

    return _FakeConfig(plugins=plugins or [])


def _make_plugin_module(name: str, *, raise_on_register: bool = False):
    """Create a fake module that acts as a plugin."""
    mod = types.ModuleType(f"_fake_plugin_{name}")
    mod.name = name  # type: ignore[attr-defined]

    def register(context):
        if raise_on_register:
            raise RuntimeError(f"boom from {name}")
        context.add_assertion(f"{name}_assert", lambda: None)

    mod.register = register  # type: ignore[attr-defined]
    return mod


# ---------------------------------------------------------------------------
# PluginContext tests
# ---------------------------------------------------------------------------


class TestPluginContext:
    def test_add_assertion(self):
        ctx = PluginContext()
        fn = lambda: None
        ctx.add_assertion("my_assert", fn)
        assert ctx.assertions["my_assert"] is fn

    def test_add_fixture(self):
        ctx = PluginContext()
        factory = lambda: None
        ctx.add_fixture("my_fix", factory, FixtureScope.PER_MODULE)
        assert len(ctx.fixtures) == 1
        assert ctx.fixtures[0] == ("my_fix", factory, FixtureScope.PER_MODULE)

    def test_add_fixture_default_scope(self):
        ctx = PluginContext()
        factory = lambda: None
        ctx.add_fixture("f", factory)
        assert ctx.fixtures[0][2] is FixtureScope.PER_TEST

    def test_add_reporter(self):
        ctx = PluginContext()

        class FakeReporter:
            def generate(self, results):
                return ""

        r = FakeReporter()
        ctx.add_reporter("custom", r)
        assert ctx.reporters["custom"] is r

    def test_add_transport(self):
        ctx = PluginContext()
        factory = lambda: None
        ctx.add_transport("custom_tp", factory)
        assert ctx.transports["custom_tp"] is factory

    def test_add_discovery_hook(self):
        ctx = PluginContext()

        def hook(test_modules):
            return test_modules

        ctx.add_discovery_hook(hook)
        assert len(ctx.discovery_hooks) == 1
        assert ctx.discovery_hooks[0] is hook


# ---------------------------------------------------------------------------
# PluginRegistry tests
# ---------------------------------------------------------------------------


class TestPluginRegistry:
    def test_register_plugin_via_module(self):
        """A module with name + register is loaded correctly (Req 9.3)."""
        registry = PluginRegistry()
        mod = _make_plugin_module("alpha")
        registry._register_plugin(mod, source="test")
        assert "alpha" in registry._loaded_names
        assert "alpha_assert" in registry.context.assertions

    def test_duplicate_name_rejected(self):
        """Second plugin with same name is skipped (Req 9.5)."""
        registry = PluginRegistry()
        mod1 = _make_plugin_module("dup")
        mod2 = _make_plugin_module("dup")
        registry._register_plugin(mod1, source="first")
        registry._register_plugin(mod2, source="second")
        assert "dup" in registry._loaded_names
        # Only one assertion registered (from first plugin)
        assert "dup_assert" in registry.context.assertions

    def test_register_error_skips_plugin(self):
        """Plugin that raises during register() is skipped (Req 9.4)."""
        registry = PluginRegistry()
        mod = _make_plugin_module("bad", raise_on_register=True)
        registry._register_plugin(mod, source="test")
        assert "bad" not in registry._loaded_names

    def test_plugin_without_name_skipped(self):
        """Plugin with no name attribute is skipped."""
        registry = PluginRegistry()
        mod = types.ModuleType("_no_name")
        mod.register = lambda ctx: None  # type: ignore[attr-defined]
        registry._register_plugin(mod, source="test")
        assert len(registry._loaded_names) == 0

    def test_discover_and_load_entry_points(self):
        """Entry-point plugins are discovered and loaded (Req 9.1)."""
        mod = _make_plugin_module("ep_plugin")

        class FakeEP:
            name = "ep_plugin"

            def load(self):
                return mod

        with patch(
            "mcp_test_harness.plugins.importlib.metadata.entry_points"
        ) as mock_eps:
            mock_eps.return_value.select.return_value = [FakeEP()]
            registry = PluginRegistry()
            registry.discover_and_load(_make_config())

        assert "ep_plugin" in registry._loaded_names

    def test_discover_and_load_config_paths(self):
        """Config-file plugin paths are loaded (Req 9.2)."""
        mod = _make_plugin_module("path_plugin")

        registry = PluginRegistry()
        with patch.object(registry, "_load_from_path") as mock_load:
            # Simulate the path loading by directly registering
            def side_effect(path_or_name):
                registry._register_plugin(mod, source=f"path:{path_or_name}")

            mock_load.side_effect = side_effect
            registry.discover_and_load(_make_config(plugins=["my_plugin_module"]))

        assert "path_plugin" in registry._loaded_names

    def test_entry_point_load_error_skipped(self):
        """Entry point that fails to load is skipped (Req 9.4)."""

        class BadEP:
            name = "broken_ep"

            def load(self):
                raise ImportError("no such module")

        with patch(
            "mcp_test_harness.plugins.importlib.metadata.entry_points"
        ) as mock_eps:
            mock_eps.return_value.select.return_value = [BadEP()]
            registry = PluginRegistry()
            registry.discover_and_load(_make_config())

        assert "broken_ep" not in registry._loaded_names

    def test_extract_plugin_from_class(self):
        """A module exposing a plugin class is extracted correctly."""
        mod = types.ModuleType("_cls_plugin")

        class MyPlugin:
            name = "cls_plug"

            def register(self, context):
                context.add_assertion("cls_assert", lambda: None)

        mod.MyPlugin = MyPlugin  # type: ignore[attr-defined]

        registry = PluginRegistry()
        plugin = registry._extract_plugin(mod)
        assert plugin is not None
        assert plugin.name == "cls_plug"

    def test_extract_plugin_from_plugin_attr(self):
        """A module with a ``plugin`` attribute is extracted."""
        mod = types.ModuleType("_attr_plugin")

        class P:
            name = "attr_plug"

            def register(self, context):
                pass

        mod.plugin = P()  # type: ignore[attr-defined]

        registry = PluginRegistry()
        plugin = registry._extract_plugin(mod)
        assert plugin is not None
        assert plugin.name == "attr_plug"

    def test_extract_plugin_returns_none_for_empty_module(self):
        """A module with no plugin interface returns None."""
        mod = types.ModuleType("_empty")
        registry = PluginRegistry()
        assert registry._extract_plugin(mod) is None


# ---------------------------------------------------------------------------
# MCPTestPlugin protocol check
# ---------------------------------------------------------------------------


class TestMCPTestPluginProtocol:
    def test_protocol_satisfied(self):
        """A class with name + register satisfies the protocol."""

        class Good:
            name = "good"

            def register(self, context: PluginContext) -> None:
                pass

        assert isinstance(Good(), MCPTestPlugin)
