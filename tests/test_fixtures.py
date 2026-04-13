"""Tests for the fixture manager (mcp_test_harness.fixtures).

Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
"""

from __future__ import annotations

import pytest

from mcp_test_harness.fixtures import (
    FixtureError,
    FixtureManager,
    FixtureScope,
    _decorated_fixtures,
    fixture,
    register_builtin_fixtures,
    register_decorated_fixtures,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeSession:
    """Minimal stand-in for mcp.ClientSession."""

    def __init__(self, label: str = "default") -> None:
        self.label = label


class _FakeManagedServer:
    """Minimal stand-in for lifecycle.ManagedServer."""

    def __init__(self, label: str = "default") -> None:
        self.session = _FakeSession(label)


# ---------------------------------------------------------------------------
# FixtureScope enum
# ---------------------------------------------------------------------------


class TestFixtureScope:
    def test_enum_values(self) -> None:
        assert FixtureScope.PER_TEST.value == "per_test"
        assert FixtureScope.PER_MODULE.value == "per_module"


# ---------------------------------------------------------------------------
# Registration and resolution by parameter name
# ---------------------------------------------------------------------------


class TestFixtureResolution:
    @pytest.mark.asyncio
    async def test_resolve_by_parameter_name(self) -> None:
        """Fixtures are resolved by matching parameter names."""
        mgr = FixtureManager()

        async def my_fixture() -> str:
            return "hello"

        mgr.register("my_fixture", my_fixture)

        async def test_fn(my_fixture: str) -> None: ...

        resolved = await mgr.resolve(test_fn)
        assert resolved == {"my_fixture": "hello"}

    @pytest.mark.asyncio
    async def test_resolve_unknown_fixture_raises(self) -> None:
        """Requesting an unregistered fixture raises FixtureError."""
        mgr = FixtureManager()

        async def test_fn(unknown: str) -> None: ...

        with pytest.raises(FixtureError, match="No fixture registered.*'unknown'"):
            await mgr.resolve(test_fn)

    @pytest.mark.asyncio
    async def test_resolve_multiple_fixtures(self) -> None:
        mgr = FixtureManager()

        async def fix_a() -> str:
            return "a"

        async def fix_b() -> int:
            return 42

        mgr.register("fix_a", fix_a)
        mgr.register("fix_b", fix_b)

        async def test_fn(fix_a: str, fix_b: int) -> None: ...

        resolved = await mgr.resolve(test_fn)
        assert resolved == {"fix_a": "a", "fix_b": 42}

    @pytest.mark.asyncio
    async def test_resolve_skips_self_parameter(self) -> None:
        """The 'self' parameter is ignored during resolution."""
        mgr = FixtureManager()

        async def fix_a() -> str:
            return "a"

        mgr.register("fix_a", fix_a)

        async def test_method(self: object, fix_a: str) -> None: ...

        resolved = await mgr.resolve(test_method)
        assert resolved == {"fix_a": "a"}


# ---------------------------------------------------------------------------
# Scoping: per-test vs per-module
# ---------------------------------------------------------------------------


class TestFixtureScoping:
    @pytest.mark.asyncio
    async def test_per_test_not_cached_across_teardowns(self) -> None:
        """Per-test fixtures are cleared after teardown."""
        call_count = 0

        async def counting_fixture() -> int:
            nonlocal call_count
            call_count += 1
            return call_count

        mgr = FixtureManager()
        mgr.register("counter", counting_fixture, FixtureScope.PER_TEST)

        async def test_fn(counter: int) -> None: ...

        r1 = await mgr.resolve(test_fn)
        assert r1["counter"] == 1

        await mgr.teardown(FixtureScope.PER_TEST)

        r2 = await mgr.resolve(test_fn)
        assert r2["counter"] == 2

    @pytest.mark.asyncio
    async def test_per_module_cached_across_resolves(self) -> None:
        """Per-module fixtures are cached and reused."""
        call_count = 0

        async def counting_fixture() -> int:
            nonlocal call_count
            call_count += 1
            return call_count

        mgr = FixtureManager()
        mgr.register("counter", counting_fixture, FixtureScope.PER_MODULE)

        async def test_fn(counter: int) -> None: ...

        r1 = await mgr.resolve(test_fn)
        r2 = await mgr.resolve(test_fn)
        assert r1["counter"] == r2["counter"] == 1
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_per_module_cleared_after_module_teardown(self) -> None:
        call_count = 0

        async def counting_fixture() -> int:
            nonlocal call_count
            call_count += 1
            return call_count

        mgr = FixtureManager()
        mgr.register("counter", counting_fixture, FixtureScope.PER_MODULE)

        async def test_fn(counter: int) -> None: ...

        await mgr.resolve(test_fn)
        await mgr.teardown(FixtureScope.PER_MODULE)

        r2 = await mgr.resolve(test_fn)
        assert r2["counter"] == 2


# ---------------------------------------------------------------------------
# Async generator (yield-based) fixtures
# ---------------------------------------------------------------------------


class TestAsyncGeneratorFixtures:
    @pytest.mark.asyncio
    async def test_yield_fixture_setup_and_teardown(self) -> None:
        """Async generator fixtures yield a value and run teardown."""
        teardown_ran = False

        async def my_gen_fixture():
            yield "setup_value"
            nonlocal teardown_ran
            teardown_ran = True

        mgr = FixtureManager()
        mgr.register("my_gen_fixture", my_gen_fixture)

        async def test_fn(my_gen_fixture: str) -> None: ...

        resolved = await mgr.resolve(test_fn)
        assert resolved["my_gen_fixture"] == "setup_value"
        assert not teardown_ran

        errors = await mgr.teardown(FixtureScope.PER_TEST)
        assert errors == []
        assert teardown_ran


# ---------------------------------------------------------------------------
# Teardown error collection (Requirement 5.4)
# ---------------------------------------------------------------------------


class TestTeardownErrors:
    @pytest.mark.asyncio
    async def test_teardown_errors_collected(self) -> None:
        """Teardown errors are collected without raising."""

        async def bad_fixture():
            yield "value"
            raise RuntimeError("teardown boom")

        mgr = FixtureManager()
        mgr.register("bad", bad_fixture)

        async def test_fn(bad: str) -> None: ...

        await mgr.resolve(test_fn)
        errors = await mgr.teardown(FixtureScope.PER_TEST)

        assert len(errors) == 1
        assert "teardown boom" in str(errors[0])

    @pytest.mark.asyncio
    async def test_multiple_teardown_errors(self) -> None:
        """Multiple teardown errors are all collected."""

        async def bad_a():
            yield "a"
            raise RuntimeError("boom a")

        async def bad_b():
            yield "b"
            raise RuntimeError("boom b")

        mgr = FixtureManager()
        mgr.register("bad_a", bad_a)
        mgr.register("bad_b", bad_b)

        async def test_fn(bad_a: str, bad_b: str) -> None: ...

        await mgr.resolve(test_fn)
        errors = await mgr.teardown(FixtureScope.PER_TEST)

        assert len(errors) == 2
        messages = {str(e) for e in errors}
        assert "boom a" in messages
        assert "boom b" in messages


# ---------------------------------------------------------------------------
# Built-in fixtures (Requirements 5.1, 5.2)
# ---------------------------------------------------------------------------


class TestBuiltinFixtures:
    @pytest.mark.asyncio
    async def test_mcp_server_fixture_per_test(self) -> None:
        """The mcp_server fixture yields the session (per-test scope)."""
        mgr = FixtureManager()
        register_builtin_fixtures(mgr)

        server = _FakeManagedServer("test-server")
        mgr.set_injected("managed_server", server)

        async def test_fn(mcp_server: object) -> None: ...

        resolved = await mgr.resolve(test_fn)
        assert resolved["mcp_server"] is server.session

    @pytest.mark.asyncio
    async def test_mcp_server_session_fixture_per_module(self) -> None:
        """The mcp_server_session fixture is per-module scoped."""
        mgr = FixtureManager()
        register_builtin_fixtures(mgr)

        server = _FakeManagedServer("shared")
        mgr.set_injected("managed_server", server)

        async def test_fn(mcp_server_session: object) -> None: ...

        r1 = await mgr.resolve(test_fn)
        r2 = await mgr.resolve(test_fn)
        assert r1["mcp_server_session"] is r2["mcp_server_session"]
        assert r1["mcp_server_session"] is server.session


# ---------------------------------------------------------------------------
# @fixture decorator (Requirement 5.5)
# ---------------------------------------------------------------------------


class TestFixtureDecorator:
    def setup_method(self) -> None:
        """Clear the global decorated fixtures list before each test."""
        _decorated_fixtures.clear()

    def test_decorator_no_parens(self) -> None:
        @fixture
        async def my_fix():
            yield 1

        assert len(_decorated_fixtures) == 1
        name, fn, scope = _decorated_fixtures[0]
        assert name == "my_fix"
        assert scope is FixtureScope.PER_TEST

    def test_decorator_with_scope(self) -> None:
        @fixture(scope=FixtureScope.PER_MODULE)
        async def shared_fix():
            yield "shared"

        assert len(_decorated_fixtures) == 1
        _, _, scope = _decorated_fixtures[0]
        assert scope is FixtureScope.PER_MODULE

    @pytest.mark.asyncio
    async def test_register_decorated_fixtures(self) -> None:
        @fixture
        async def custom_data():
            return {"key": "value"}

        mgr = FixtureManager()
        register_decorated_fixtures(mgr)

        async def test_fn(custom_data: dict) -> None: ...

        resolved = await mgr.resolve(test_fn)
        assert resolved["custom_data"] == {"key": "value"}


# ---------------------------------------------------------------------------
# Injected dependencies
# ---------------------------------------------------------------------------


class TestInjectedDependencies:
    @pytest.mark.asyncio
    async def test_injected_resolved_directly(self) -> None:
        """Injected values are resolved without needing a fixture."""
        mgr = FixtureManager()
        mgr.set_injected("config", {"timeout": 30})

        async def test_fn(config: dict) -> None: ...

        resolved = await mgr.resolve(test_fn)
        assert resolved["config"] == {"timeout": 30}

    @pytest.mark.asyncio
    async def test_injected_passed_to_fixture_factory(self) -> None:
        """Fixture factories can depend on injected values."""
        mgr = FixtureManager()
        mgr.set_injected("base_url", "http://localhost:8080")

        async def api_client(base_url: str) -> str:
            return f"client({base_url})"

        mgr.register("api_client", api_client)

        async def test_fn(api_client: str) -> None: ...

        resolved = await mgr.resolve(test_fn)
        assert resolved["api_client"] == "client(http://localhost:8080)"
