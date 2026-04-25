"""Extra plugin tests -- cover file path loading, import errors, edge cases."""

from __future__ import annotations

import types
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from mcp_test_harness.plugins import PluginRegistry, PluginContext


class TestLoadFromFilePath:
    def test_load_py_file(self, tmp_path: Path):
        plugin_file = tmp_path / "my_plugin.py"
        plugin_file.write_text(
            'name = "file_plugin"\n'
            'def register(context):\n'
            '    context.add_assertion("file_assert", lambda: None)\n'
        )
        registry = PluginRegistry()
        registry._load_from_path(str(plugin_file))
        assert "file_plugin" in registry._loaded_names
        assert "file_assert" in registry.context.assertions

    def test_load_nonexistent_file_skips(self):
        registry = PluginRegistry()
        registry._load_from_path("/nonexistent/path/plugin.py")
        assert len(registry._loaded_names) == 0

    def test_load_invalid_python_file_skips(self, tmp_path: Path):
        bad_file = tmp_path / "bad_plugin.py"
        bad_file.write_text("this is not valid python !!@#$%\n")
        registry = PluginRegistry()
        registry._load_from_path(str(bad_file))
        assert len(registry._loaded_names) == 0

    def test_load_module_without_plugin_interface_skips(self, tmp_path: Path):
        no_plugin = tmp_path / "no_plugin.py"
        no_plugin.write_text("x = 42\n")
        registry = PluginRegistry()
        registry._load_from_path(str(no_plugin))
        assert len(registry._loaded_names) == 0


class TestLoadFromModuleName:
    def test_load_dotted_module(self):
        mod = types.ModuleType("fake_dotted_module")
        mod.name = "dotted_plug"  # type: ignore[attr-defined]
        mod.register = lambda ctx: ctx.add_assertion("dot_assert", lambda: None)  # type: ignore[attr-defined]

        registry = PluginRegistry()
        with patch("mcp_test_harness.plugins.importlib.import_module", return_value=mod):
            registry._load_from_path("fake_dotted_module")
        assert "dotted_plug" in registry._loaded_names

    def test_import_error_skips(self):
        registry = PluginRegistry()
        with patch(
            "mcp_test_harness.plugins.importlib.import_module",
            side_effect=ImportError("no such module"),
        ):
            registry._load_from_path("nonexistent_module")
        assert len(registry._loaded_names) == 0


class TestExtractPluginFromClass:
    def test_class_with_init_error_skipped(self):
        mod = types.ModuleType("_bad_cls")

        class BadPlugin:
            name = "bad"
            def __init__(self):
                raise RuntimeError("init failed")
            def register(self, ctx):
                pass

        mod.BadPlugin = BadPlugin  # type: ignore[attr-defined]
        registry = PluginRegistry()
        result = registry._extract_plugin(mod)
        assert result is None


class TestDiscoverAndLoadFull:
    def test_entry_points_and_config_paths(self, tmp_path: Path):
        plugin_file = tmp_path / "cfg_plugin.py"
        plugin_file.write_text(
            'name = "cfg_plug"\n'
            'def register(context):\n'
            '    context.add_assertion("cfg_assert", lambda: None)\n'
        )

        class FakeConfig:
            plugins = [str(plugin_file)]

        with patch(
            "mcp_test_harness.plugins.importlib.metadata.entry_points"
        ) as mock_eps:
            mock_eps.return_value.select.return_value = []
            registry = PluginRegistry()
            registry.discover_and_load(FakeConfig())

        assert "cfg_plug" in registry._loaded_names

    def test_entry_points_fallback_dict_style(self):
        """Test fallback for older Python where entry_points returns a dict."""
        mod = types.ModuleType("_ep_mod")
        mod.name = "ep_dict"  # type: ignore[attr-defined]
        mod.register = lambda ctx: None  # type: ignore[attr-defined]

        class FakeEP:
            name = "ep_dict"
            def load(self):
                return mod

        class FakeConfig:
            plugins = []

        # Simulate dict-style return (no .select method)
        eps_dict = {"mcp_test_harness": [FakeEP()]}

        with patch(
            "mcp_test_harness.plugins.importlib.metadata.entry_points",
            return_value=eps_dict,
        ):
            registry = PluginRegistry()
            registry.discover_and_load(FakeConfig())

        assert "ep_dict" in registry._loaded_names


class TestRuntimeWiring:
    def test_expose_assertions_adds_to_package(self):
        called = {"ok": False}

        def _plug_assert():
            called["ok"] = True

        ctx = PluginContext()
        ctx.add_assertion("plug_assert", _plug_assert)
        registry = PluginRegistry(context=ctx)
        registry.expose_assertions()

        import mcp_test_harness

        assert hasattr(mcp_test_harness, "plug_assert")
        mcp_test_harness.plug_assert()
        assert called["ok"] is True
        assert "plug_assert" in mcp_test_harness.__all__

    def test_apply_discovery_hooks_chains_outputs(self):
        ctx = PluginContext()
        ctx.add_discovery_hook(lambda mods: mods + ["a"])
        ctx.add_discovery_hook(lambda mods: mods + ["b"])
        registry = PluginRegistry(context=ctx)
        assert registry.apply_discovery_hooks([]) == ["a", "b"]

    def test_apply_discovery_hooks_logs_and_continues_on_error(self):
        ctx = PluginContext()
        ctx.add_discovery_hook(lambda mods: (_ for _ in ()).throw(RuntimeError("boom")))
        ctx.add_discovery_hook(lambda mods: mods + ["ok"])
        registry = PluginRegistry(context=ctx)
        assert registry.apply_discovery_hooks([]) == ["ok"]

    def test_expose_assertions_import_failure_is_safe(self):
        ctx = PluginContext()
        ctx.add_assertion("x", lambda: None)
        registry = PluginRegistry(context=ctx)
        with patch("mcp_test_harness.plugins.importlib.import_module", side_effect=ImportError("x")):
            registry.expose_assertions()
