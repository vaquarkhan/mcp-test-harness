"""Plugin registry for the MCP Test Harness.

Discovers and loads plugins from Python entry points
(``mcp_test_harness`` group) and config-file paths, then invokes each
plugin's ``register(context)`` function to collect custom assertions,
fixtures, reporters, transports, and discovery hooks.

Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6
"""

from __future__ import annotations

import importlib
import importlib.metadata
import importlib.util
import logging
import sys
import traceback
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from mcp_test_harness.fixtures import FixtureScope

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# DiscoveryHook protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class DiscoveryHook(Protocol):
    """Callable invoked during test discovery to augment the test list."""

    def __call__(self, test_modules: list[Any]) -> list[Any]: ...


# ---------------------------------------------------------------------------
# Reporter protocol (re-exported for convenience)
# ---------------------------------------------------------------------------


@runtime_checkable
class Reporter(Protocol):
    """Interface that reporters must satisfy."""

    def generate(self, results: Any) -> str: ...


# ---------------------------------------------------------------------------
# MCPTestPlugin protocol  (Requirement 9.6)
# ---------------------------------------------------------------------------


@runtime_checkable
class MCPTestPlugin(Protocol):
    """Interface that plugins must implement.

    Each plugin must expose a ``name`` attribute and a ``register``
    method that receives a :class:`PluginContext`.
    """

    name: str

    def register(self, context: PluginContext) -> None:
        """Called during plugin loading.  Use *context* to register extensions."""
        ...


# ---------------------------------------------------------------------------
# PluginContext  (Requirement 9.3)
# ---------------------------------------------------------------------------


class PluginContext:
    """Registration context passed to each plugin's ``register()`` method.

    Plugins use the ``add_*`` helpers to contribute custom assertions,
    fixtures, reporters, transport adapters, and discovery hooks.
    """

    def __init__(self) -> None:
        self.assertions: dict[str, Callable[..., Any]] = {}
        self.fixtures: list[tuple[str, Callable[..., Any], FixtureScope]] = []
        self.reporters: dict[str, Reporter] = {}
        self.transports: dict[str, Callable[..., Any]] = {}
        self.discovery_hooks: list[DiscoveryHook] = []

    # -- registration helpers -----------------------------------------------

    def add_assertion(self, name: str, func: Callable[..., Any]) -> None:
        """Register a custom assertion function under *name*."""
        self.assertions[name] = func

    def add_fixture(
        self,
        name: str,
        factory: Callable[..., Any],
        scope: FixtureScope = FixtureScope.PER_TEST,
    ) -> None:
        """Register a custom fixture factory."""
        self.fixtures.append((name, factory, scope))

    def add_reporter(self, name: str, reporter: Reporter) -> None:
        """Register a custom reporter under *name*."""
        self.reporters[name] = reporter

    def add_transport(self, name: str, adapter_factory: Callable[..., Any]) -> None:
        """Register a custom transport adapter factory under *name*."""
        self.transports[name] = adapter_factory

    def add_discovery_hook(self, hook: DiscoveryHook) -> None:
        """Register a hook called during test discovery."""
        self.discovery_hooks.append(hook)


# ---------------------------------------------------------------------------
# PluginRegistry  (Requirements 9.1, 9.2, 9.4, 9.5)
# ---------------------------------------------------------------------------


@dataclass
class PluginRegistry:
    """Discovers, loads, and manages plugins.

    Call :meth:`discover_and_load` with a ``HarnessConfig`` to populate
    the :attr:`context` with all registered extensions.
    """

    context: PluginContext = field(default_factory=PluginContext)
    _loaded_names: set[str] = field(default_factory=set, repr=False)

    def discover_and_load(self, config: Any) -> None:
        """Load plugins from entry points and config-file paths.

        Parameters
        ----------
        config:
            A ``HarnessConfig`` instance.  The ``plugins`` attribute is
            expected to be a list of strings -- either installed package
            names (discovered via entry points) or file-system paths to
            Python modules.
        """
        # 1. Entry-point discovery  (Requirement 9.1)
        self._load_from_entry_points()

        # 2. Config-file paths  (Requirement 9.2)
        plugin_paths: list[str] = getattr(config, "plugins", []) or []
        for path_or_name in plugin_paths:
            self._load_from_path(path_or_name)

    def register_fixtures(self, manager: Any) -> None:
        """Register plugin-provided fixtures into a FixtureManager."""
        for name, factory, scope in self.context.fixtures:
            manager.register(name, factory, scope)

    def expose_assertions(self) -> None:
        """Expose plugin assertions via package namespaces.

        This makes plugin assertions available as attributes on both
        ``mcp_test_harness`` and ``mcp_test_harness.assertions`` so user
        tests can call them naturally after plugin load.
        """
        if not self.context.assertions:
            return
        try:
            pkg = importlib.import_module("mcp_test_harness")
            assertions_mod = importlib.import_module("mcp_test_harness.assertions")
        except Exception:  # noqa: BLE001
            logger.debug("Could not import harness modules to expose assertions", exc_info=True)
            return

        for name, func in self.context.assertions.items():
            setattr(pkg, name, func)
            setattr(assertions_mod, name, func)
            all_list = getattr(pkg, "__all__", None)
            if isinstance(all_list, list) and name not in all_list:
                all_list.append(name)

    def apply_discovery_hooks(self, test_modules: list[Any]) -> list[Any]:
        """Apply plugin discovery hooks in registration order."""
        out = test_modules
        for hook in self.context.discovery_hooks:
            try:
                out = hook(out)
            except Exception:  # noqa: BLE001
                logger.error("Discovery hook failed: %s", traceback.format_exc())
        return out

    # ------------------------------------------------------------------
    # Internal: entry-point loading
    # ------------------------------------------------------------------

    def _load_from_entry_points(self) -> None:
        """Discover plugins registered under the ``mcp_test_harness`` group."""
        try:
            eps = importlib.metadata.entry_points()
        except Exception:  # noqa: BLE001
            logger.debug("Failed to query entry points", exc_info=True)
            return

        # Python 3.12+ returns a SelectableGroups / list; 3.9+ has .select()
        if hasattr(eps, "select"):
            group_eps = eps.select(group="mcp_test_harness")
        else:
            # Fallback for older dict-style return
            group_eps = eps.get("mcp_test_harness", [])  # type: ignore[union-attr]

        for ep in group_eps:
            try:
                plugin_obj = ep.load()
            except Exception:  # noqa: BLE001
                logger.error(
                    "Failed to load plugin entry point '%s': %s",
                    ep.name,
                    traceback.format_exc(),
                )
                continue

            self._register_plugin(plugin_obj, source=f"entry_point:{ep.name}")

    # ------------------------------------------------------------------
    # Internal: file-path / module-name loading
    # ------------------------------------------------------------------

    def _load_from_path(self, path_or_name: str) -> None:
        """Load a plugin from a file path or dotted module name."""
        module: Any = None

        # Try as a file path first
        if path_or_name.endswith(".py") or "/" in path_or_name or "\\" in path_or_name:
            module = self._import_file(path_or_name)
        else:
            # Treat as a dotted module name
            try:
                module = importlib.import_module(path_or_name)
            except Exception:  # noqa: BLE001
                logger.error(
                    "Failed to import plugin module '%s': %s",
                    path_or_name,
                    traceback.format_exc(),
                )
                return

        if module is None:
            return

        # The module itself may be the plugin (has name + register),
        # or it may expose a plugin object / class.
        plugin_obj = self._extract_plugin(module)
        if plugin_obj is not None:
            self._register_plugin(plugin_obj, source=f"path:{path_or_name}")
        else:
            logger.error(
                "Plugin '%s' does not expose a valid MCPTestPlugin "
                "(must have 'name' attribute and 'register' method)",
                path_or_name,
            )

    def _import_file(self, file_path: str) -> Any:
        """Import a Python file as a module."""
        try:
            module_name = f"_mcp_plugin_{file_path.replace('/', '_').replace('.', '_')}"
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec is None or spec.loader is None:
                logger.error("Cannot create module spec for plugin file '%s'", file_path)
                return None
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            return module
        except Exception:  # noqa: BLE001
            logger.error(
                "Failed to load plugin file '%s': %s",
                file_path,
                traceback.format_exc(),
            )
            return None

    # ------------------------------------------------------------------
    # Internal: plugin extraction and registration
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_plugin(module: Any) -> Any:
        """Extract a plugin object from a loaded module.

        The module itself is checked first (it may have ``name`` and
        ``register`` at module level).  Then we look for a ``plugin``
        attribute or any class implementing :class:`MCPTestPlugin`.
        """
        # Module-level name + register
        if hasattr(module, "name") and hasattr(module, "register") and callable(module.register):
            return module

        # Explicit ``plugin`` attribute
        if hasattr(module, "plugin"):
            candidate = module.plugin
            if hasattr(candidate, "name") and hasattr(candidate, "register"):
                return candidate

        # Scan for a class implementing the protocol
        for attr_name in dir(module):
            obj = getattr(module, attr_name, None)
            if (
                obj is not None
                and isinstance(obj, type)
                and hasattr(obj, "name")
                and hasattr(obj, "register")
            ):
                # Instantiate the class
                try:
                    instance = obj()
                    if hasattr(instance, "name") and callable(getattr(instance, "register", None)):
                        return instance
                except Exception:  # noqa: BLE001
                    continue

        return None

    def _register_plugin(self, plugin_obj: Any, *, source: str) -> None:
        """Invoke the plugin's ``register(context)`` with duplicate-name guard."""
        plugin_name = getattr(plugin_obj, "name", None)
        if not plugin_name:
            logger.error(
                "Plugin from %s has no 'name' attribute; skipping",
                source,
            )
            return

        # Requirement 9.5 -- unique names
        if plugin_name in self._loaded_names:
            logger.error(
                "Duplicate plugin name '%s' (from %s); "
                "keeping the first loaded instance",
                plugin_name,
                source,
            )
            return

        # Requirement 9.3 -- invoke register(context)
        try:
            plugin_obj.register(self.context)
        except Exception:  # noqa: BLE001
            # Requirement 9.4 -- log and skip
            logger.error(
                "Plugin '%s' (from %s) raised an error during register(): %s",
                plugin_name,
                source,
                traceback.format_exc(),
            )
            return

        self._loaded_names.add(plugin_name)
        logger.info("Loaded plugin '%s' from %s", plugin_name, source)
