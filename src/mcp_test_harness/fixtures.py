"""Fixture manager for the MCP Test Harness.

Provides a lightweight fixture system with:
- Per-test and per-module scoping
- Async generator (yield-based) setup/teardown
- Parameter-name-based resolution via ``inspect.signature()``
- Built-in ``mcp_server`` and ``mcp_server_session`` fixtures
- User-defined custom fixtures via ``@fixture`` decorator

Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
"""

from __future__ import annotations

import inspect
import logging
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# FixtureScope enum
# ---------------------------------------------------------------------------


class FixtureScope(Enum):
    """Scope controlling fixture lifetime."""

    PER_TEST = "per_test"
    PER_MODULE = "per_module"


# ---------------------------------------------------------------------------
# FixtureDefinition (internal)
# ---------------------------------------------------------------------------


@dataclass
class _FixtureDefinition:
    """Internal record for a registered fixture."""

    name: str
    factory: Callable[..., Any]
    scope: FixtureScope


# ---------------------------------------------------------------------------
# FixtureManager
# ---------------------------------------------------------------------------


class FixtureManager:
    """Manages fixture registration, resolution, and teardown.

    The manager maintains a registry of fixture factories keyed by name.
    When a test function is about to run, ``resolve()`` inspects its
    parameter names and instantiates the required fixtures, caching
    per-module fixtures so they are shared across tests in the same module.

    Teardown is performed by driving any async-generator fixtures past
    their ``yield`` point.  Teardown errors are collected and returned
    without altering the test's pass/fail status (Requirement 5.4).
    """

    def __init__(self) -> None:
        self._registry: dict[str, _FixtureDefinition] = {}
        # Caches: name -> resolved value
        self._per_test_cache: dict[str, Any] = {}
        self._per_module_cache: dict[str, Any] = {}
        # Generators that need teardown (driven past yield)
        self._per_test_generators: list[tuple[str, AsyncIterator[Any]]] = []
        self._per_module_generators: list[tuple[str, AsyncIterator[Any]]] = []
        # Injected dependencies available to fixture factories
        self._injected: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Dependency injection for built-in fixtures
    # ------------------------------------------------------------------

    def set_injected(self, name: str, value: Any) -> None:
        """Make *value* available as an injectable dependency for fixtures.

        The executor uses this to inject ``managed_server`` so that the
        built-in ``mcp_server`` / ``mcp_server_session`` fixtures can
        access the running server without being coupled to the lifecycle
        manager directly.
        """
        self._injected[name] = value

    # ------------------------------------------------------------------
    # register
    # ------------------------------------------------------------------

    def register(
        self,
        name: str,
        factory: Callable[..., Any],
        scope: FixtureScope = FixtureScope.PER_TEST,
    ) -> None:
        """Register a fixture factory under *name*.

        Parameters
        ----------
        name:
            The parameter name that test functions use to request this
            fixture.
        factory:
            An async generator function (yield-based) or an async/sync
            callable that produces the fixture value.
        scope:
            ``PER_TEST`` (default) -- created and torn down for every test.
            ``PER_MODULE`` -- created once per module and shared.
        """
        self._registry[name] = _FixtureDefinition(
            name=name,
            factory=factory,
            scope=scope,
        )

    # ------------------------------------------------------------------
    # resolve
    # ------------------------------------------------------------------

    async def resolve(self, func: Callable[..., Any]) -> dict[str, Any]:
        """Resolve all fixtures required by *func* via parameter inspection.

        Uses ``inspect.signature()`` to determine which parameters the
        test function (or fixture factory) expects, then looks each one
        up in the registry and instantiates it if not already cached.

        Parameters
        ----------
        func:
            The test function whose parameters should be resolved.

        Returns
        -------
        dict[str, Any]
            Mapping of parameter name to fixture value.

        Raises
        ------
        FixtureError
            If a required parameter has no registered fixture.
        """
        sig = inspect.signature(func)
        resolved: dict[str, Any] = {}

        for param_name in sig.parameters:
            if param_name == "self":
                continue

            value = await self._resolve_one(param_name)
            resolved[param_name] = value

        return resolved

    # ------------------------------------------------------------------
    # teardown
    # ------------------------------------------------------------------

    async def teardown(self, scope: FixtureScope) -> list[Exception]:
        """Tear down all fixtures for *scope*, collecting errors.

        Drives async-generator fixtures past their ``yield`` point.
        Any exceptions raised during teardown are collected and returned
        -- they do **not** alter the test's pass/fail status (Req 5.4).

        Returns
        -------
        list[Exception]
            Errors encountered during teardown (may be empty).
        """
        errors: list[Exception] = []

        if scope is FixtureScope.PER_TEST:
            generators = self._per_test_generators
            self._per_test_cache.clear()
        else:
            generators = self._per_module_generators
            self._per_module_cache.clear()

        # Teardown in reverse order (LIFO)
        for name, gen in reversed(generators):
            try:
                await gen.__anext__()
            except StopAsyncIteration:
                pass
            except Exception as exc:  # noqa: BLE001
                logger.warning("Fixture '%s' teardown error: %s", name, exc)
                errors.append(exc)

        generators.clear()
        return errors

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _resolve_one(self, name: str) -> Any:
        """Resolve a single fixture by *name*, using caches as appropriate."""
        # Check injected dependencies first (e.g. managed_server)
        if name in self._injected:
            return self._injected[name]

        defn = self._registry.get(name)
        if defn is None:
            raise FixtureError(
                f"No fixture registered for parameter '{name}'. "
                f"Available fixtures: {', '.join(sorted(self._registry)) or '(none)'}"
            )

        # Check cache
        if defn.scope is FixtureScope.PER_MODULE and name in self._per_module_cache:
            return self._per_module_cache[name]
        if defn.scope is FixtureScope.PER_TEST and name in self._per_test_cache:
            return self._per_test_cache[name]

        # Resolve any dependencies the factory itself needs
        factory_kwargs = await self._resolve_factory_deps(defn.factory)

        # Instantiate
        value = await self._instantiate(defn, factory_kwargs)

        # Cache
        if defn.scope is FixtureScope.PER_MODULE:
            self._per_module_cache[name] = value
        else:
            self._per_test_cache[name] = value

        return value

    async def _resolve_factory_deps(self, factory: Callable[..., Any]) -> dict[str, Any]:
        """Resolve dependencies that a fixture factory itself requires."""
        sig = inspect.signature(factory)
        kwargs: dict[str, Any] = {}
        for param_name in sig.parameters:
            if param_name == "self":
                continue
            # Try injected deps first, then registered fixtures
            if param_name in self._injected:
                kwargs[param_name] = self._injected[param_name]
            elif param_name in self._registry:
                kwargs[param_name] = await self._resolve_one(param_name)
        return kwargs

    async def _instantiate(
        self,
        defn: _FixtureDefinition,
        kwargs: dict[str, Any],
    ) -> Any:
        """Call the fixture factory and return the fixture value.

        Handles three factory styles:
        1. Async generator (``async def f(): yield value``) -- drive to
           yield, stash generator for teardown.
        2. Async callable -- ``await factory(**kwargs)``.
        3. Sync callable -- ``factory(**kwargs)``.
        """
        result = defn.factory(**kwargs)

        # Async generator
        if inspect.isasyncgen(result):
            gen = result
            try:
                value = await gen.__anext__()
            except StopAsyncIteration:
                raise FixtureError(
                    f"Fixture '{defn.name}' async generator did not yield a value"
                )
            # Stash for teardown
            if defn.scope is FixtureScope.PER_MODULE:
                self._per_module_generators.append((defn.name, gen))
            else:
                self._per_test_generators.append((defn.name, gen))
            return value

        # Regular awaitable
        if inspect.isawaitable(result):
            return await result

        # Sync return
        return result


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class FixtureError(Exception):
    """Raised when fixture resolution or setup fails."""


# ---------------------------------------------------------------------------
# @fixture decorator  (Requirement 5.5)
# ---------------------------------------------------------------------------

# Module-level registry used by the decorator. The FixtureManager picks
# these up when ``register_decorated_fixtures()`` is called.
_decorated_fixtures: list[tuple[str, Callable[..., Any], FixtureScope]] = []


def fixture(
    func: Callable[..., Any] | None = None,
    *,
    scope: FixtureScope = FixtureScope.PER_TEST,
) -> Any:
    """Decorator to register a user-defined fixture.

    Usage::

        from mcp_test_harness.fixtures import fixture, FixtureScope

        @fixture
        async def my_data():
            data = {"key": "value"}
            yield data
            # teardown here

        @fixture(scope=FixtureScope.PER_MODULE)
        async def shared_resource():
            resource = await create_resource()
            yield resource
            await resource.close()
    """
    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        _decorated_fixtures.append((fn.__name__, fn, scope))
        # Mark the function so it can be identified
        fn._is_fixture = True  # type: ignore[attr-defined]
        return fn

    if func is not None:
        # Used as @fixture without parentheses
        return decorator(func)

    # Used as @fixture(...) with arguments
    return decorator


def register_decorated_fixtures(manager: FixtureManager) -> None:
    """Register all ``@fixture``-decorated functions with *manager*."""
    for name, factory, scope in _decorated_fixtures:
        manager.register(name, factory, scope)


# ---------------------------------------------------------------------------
# Built-in fixtures  (Requirements 5.1, 5.2)
# ---------------------------------------------------------------------------


async def _mcp_server_fixture(managed_server: Any) -> AsyncIterator[Any]:
    """Built-in ``mcp_server`` fixture -- per-test scope.

    Yields the ``ClientSession`` from the managed server.  The session
    is the same one established during the server lifecycle start-up;
    the executor is responsible for injecting ``managed_server`` via
    ``FixtureManager.set_injected()``.

    Requirement 5.1
    """
    yield managed_server.session


async def _mcp_server_session_fixture(managed_server: Any) -> AsyncIterator[Any]:
    """Built-in ``mcp_server_session`` fixture -- per-module scope.

    Yields a shared ``ClientSession`` that persists across all tests in
    the same module.  The underlying server instance is reused.

    Requirement 5.2
    """
    yield managed_server.session


def register_builtin_fixtures(manager: FixtureManager) -> None:
    """Register the built-in ``mcp_server`` and ``mcp_server_session`` fixtures."""
    manager.register("mcp_server", _mcp_server_fixture, FixtureScope.PER_TEST)
    manager.register(
        "mcp_server_session", _mcp_server_session_fixture, FixtureScope.PER_MODULE
    )
