from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

from mcp_test_harness import __all__ as harness_exports
from mcp_test_harness.config import validate_config_file


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _FakeSession:
    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        return SimpleNamespace(content=[{"text": "ok", "isError": False}])


def test_new_security_assertions_exported() -> None:
    assert "assert_tool_denied" in harness_exports
    assert "assert_authorization_boundary" in harness_exports


def test_feature_demo_yaml_configs_match_schema() -> None:
    root = _repo_root()
    yaml_paths = [
        root / "examples/feature-demo/functional-testing/mcp_test_functional_demo.yaml",
        root / "examples/feature-demo/regression-testing/mcp_test_regression_demo.yaml",
        root / "examples/feature-demo/performance-testing/mcp_test_performance_demo.yaml",
        root / "examples/feature-demo/responsible-ai/mcp_test_responsible_ai_demo.yaml",
        root / "examples/feature-demo/usa-interest/mcp_test_usa_interest_demo.yaml",
        root / "examples/feature-demo/eu-ai-act/mcp_test_eu_ai_act_demo.yaml",
    ]
    for path in yaml_paths:
        errors = validate_config_file(path)
        assert errors == [], f"{path} has config errors: {errors}"


def test_regression_demo_snapshot_call_has_required_args() -> None:
    root = _repo_root()
    mod = _load_module(
        root / "examples/feature-demo/regression-testing/test_regression_demo.py",
        "regression_demo_module",
    )
    called: dict[str, Any] = {}

    async def _fake_snapshot(actual: Any, snapshot_name: str, test_file: Path, **_: Any) -> None:
        called["snapshot_name"] = snapshot_name
        called["test_file"] = test_file

    mod.assert_snapshot = _fake_snapshot
    asyncio.run(mod.test_regression_snapshot_stable(_FakeSession()))
    assert called["snapshot_name"] == "regression_echo"
    assert isinstance(called["test_file"], Path)


def test_performance_demo_uses_aggregate_keyword() -> None:
    root = _repo_root()
    mod = _load_module(
        root / "examples/feature-demo/performance-testing/test_performance_demo.py",
        "performance_demo_module",
    )
    calls: list[dict[str, Any]] = []

    async def _fake_latency(*args: Any, **kwargs: Any) -> None:
        calls.append(kwargs)

    mod.assert_latency = _fake_latency
    asyncio.run(mod.test_performance_latency_p95(_FakeSession()))
    asyncio.run(mod.test_performance_latency_p99(_FakeSession()))
    assert calls[0]["aggregate"] == "p95"
    assert calls[1]["aggregate"] == "p99"
