"""Tests for deterministic MCP manifest / rug-pull gate."""

from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_test_harness.assertions import MCPAssertionError
from mcp_test_harness.config import HarnessConfig, load_config, validate_config_file
from mcp_test_harness.discovery import HarnessCase
from mcp_test_harness.lifecycle import ManagedServer, StartupError
from mcp_test_harness.manifest_gate import (
    ManifestGatePolicy,
    _diff_summary,
    _item_list,
    _normalize_prompt,
    _normalize_resource,
    _normalize_tool,
    _to_plain,
    assert_manifest_snapshot,
    capture_server_manifest,
    evaluate_manifest_gate_error,
    normalize_manifest,
    parse_manifest_gate_policy,
    run_configured_manifest_gate,
    run_manifest,
    run_manifest_async,
)
from mcp_test_harness.models import CaseResult, CaseStatus
from mcp_test_harness.scheduler import HarnessScheduler
from mcp_test_harness.snapshots import (
    reset_cli_update_snapshots,
    set_cli_update_snapshots,
)


class _FakeSession:
    def __init__(self, tools=None, resources=None, prompts=None, *, explode=False):
        self._tools = tools or []
        self._resources = resources or []
        self._prompts = prompts or []
        self._explode = explode
        self.capabilities = {"tools": {}}

    async def list_tools(self):
        if self._explode:
            raise RuntimeError("tools down")
        return SimpleNamespace(tools=self._tools)

    async def list_resources(self):
        if self._explode:
            raise RuntimeError("resources down")
        return SimpleNamespace(resources=self._resources)

    async def list_prompts(self):
        if self._explode:
            raise RuntimeError("prompts down")
        return SimpleNamespace(prompts=self._prompts)


def _ns(**kwargs: object) -> Namespace:
    defaults = {
        "server_command": None,
        "transport": None,
        "config": None,
        "timeout": None,
        "verbose": None,
        "parallel": None,
        "workers": None,
        "report_format": None,
        "report_output": None,
        "sarif_output": None,
        "cra_output": None,
        "pr_summary_output": None,
        "update_snapshots": None,
        "filter_name": None,
        "filter_marker": None,
        "test_path": None,
        "list": None,
        "watch": None,
    }
    defaults.update(kwargs)
    return Namespace(**defaults)


# ---------------------------------------------------------------------------
# Capture / normalize helpers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_capture_and_normalize_sorted() -> None:
    session = _FakeSession(
        tools=[
            {"name": "z", "description": "Z", "inputSchema": {"type": "object"}},
            {"name": "a", "description": "A", "inputSchema": {"type": "object"}},
        ],
        resources=[{"uri": "res://b"}, {"uri": "res://a"}],
        prompts=[{"name": "p2"}, {"name": "p1"}],
    )
    manifest = await capture_server_manifest(
        session, capabilities={"tools": {}}, protocol_version="2025-03-26"
    )
    assert [t["name"] for t in manifest["tools"]] == ["a", "z"]
    assert [r["uri"] for r in manifest["resources"]] == ["res://a", "res://b"]
    assert [p["name"] for p in manifest["prompts"]] == ["p1", "p2"]
    assert manifest["protocolVersion"] == "2025-03-26"


@pytest.mark.asyncio
async def test_capture_handles_list_errors_and_init_result() -> None:
    session = _FakeSession(explode=True)
    session.init_result = SimpleNamespace(protocolVersion="from-init")
    manifest = await capture_server_manifest(session)
    assert manifest["tools"] == []
    assert manifest["resources"] == []
    assert manifest["prompts"] == []
    assert manifest["protocolVersion"] == "from-init"


@pytest.mark.asyncio
async def test_capture_protocol_from_dict_init() -> None:
    session = _FakeSession()
    session.initialize_result = {"protocolVersion": "dict-proto"}
    manifest = await capture_server_manifest(session, capabilities=None)
    assert manifest["protocolVersion"] == "dict-proto"


def test_to_plain_and_normalize_edges() -> None:
    class DumpOk:
        def model_dump(self, **_kwargs):
            return {"name": "t", "description": "d"}

    class DumpTypeError:
        def model_dump(self, **kwargs):
            if kwargs:
                raise TypeError("no kwargs")
            return {"name": "u"}

    class DumpFail:
        def model_dump(self, **_kwargs):
            raise RuntimeError("boom")

        def __str__(self) -> str:
            return "DumpFail"

    class AttrObj:
        def __init__(self) -> None:
            self.name = "attr"
            self._hidden = 1

        def method(self) -> None:
            return None

    assert _to_plain(None) is None
    assert _to_plain(("a", 1)) == ["a", 1]
    assert _to_plain(DumpOk())["name"] == "t"
    assert _to_plain(DumpTypeError())["name"] == "u"
    assert _to_plain(DumpFail()) == "DumpFail"
    assert _to_plain(AttrObj())["name"] == "attr"
    assert _normalize_tool("x") == {"raw": "x"}
    assert _normalize_resource("r") == {"raw": "r"}
    assert _normalize_prompt("p") == {"raw": "p"}
    assert normalize_manifest({"capabilities": "odd"})["capabilities"] == {"value": "odd"}
    assert _item_list({"tool": [{"name": "a"}]}, "tool") == [{"name": "a"}]
    assert _item_list([{"name": "b"}], "tool") == [{"name": "b"}]
    assert _item_list({"other": 1}, "tool") == []
    assert _item_list("nope", "tool") == []


def test_diff_summary_sections() -> None:
    stored = {
        "tools": [{"name": "a", "description": "old"}],
        "resources": [{"uri": "res://gone"}],
        "prompts": [{"name": "p"}],
        "capabilities": {"tools": {}},
        "protocolVersion": "v1",
    }
    actual = {
        "tools": [{"name": "a", "description": "new"}, {"name": "b"}],
        "resources": [],
        "prompts": [{"name": "p"}],
        "capabilities": {"tools": {"listChanged": True}},
        "protocolVersion": "v2",
    }
    summary = _diff_summary(stored, actual)
    assert "tools added: b" in summary
    assert "tools changed: a" in summary
    assert "resources removed" in summary
    assert "capabilities changed" in summary
    assert "protocolVersion changed" in summary
    assert "manifest JSON differs" in _diff_summary(
        {"tools": [], "resources": [], "prompts": [], "capabilities": {}, "protocolVersion": ""},
        {"tools": [], "resources": [], "prompts": [], "capabilities": {}, "protocolVersion": ""},
    )


# ---------------------------------------------------------------------------
# assert_manifest_snapshot
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_assert_manifest_creates_then_matches(tmp_path: Path) -> None:
    path = tmp_path / "mcp_manifest.snap"
    session = _FakeSession(
        tools=[{"name": "echo", "description": "Echo", "inputSchema": {"type": "object"}}]
    )
    await assert_manifest_snapshot(session, path, protocol_version="v1")
    assert path.is_file()
    await assert_manifest_snapshot(session, path, protocol_version="v1")


@pytest.mark.asyncio
async def test_assert_manifest_detects_rug_pull(tmp_path: Path) -> None:
    path = tmp_path / "mcp_manifest.snap"
    session = _FakeSession(
        tools=[{"name": "echo", "description": "Echo", "inputSchema": {"type": "object"}}]
    )
    await assert_manifest_snapshot(session, path, protocol_version="v1")
    session._tools.append(
        {"name": "evil", "description": "new", "inputSchema": {"type": "object"}}
    )
    with pytest.raises(MCPAssertionError, match="rug-pull|added"):
        await assert_manifest_snapshot(session, path, protocol_version="v1")


@pytest.mark.asyncio
async def test_assert_manifest_update_rewrites(tmp_path: Path) -> None:
    path = tmp_path / "mcp_manifest.snap"
    session = _FakeSession(
        tools=[{"name": "echo", "description": "Echo", "inputSchema": {"type": "object"}}]
    )
    await assert_manifest_snapshot(session, path)
    session._tools[0]["description"] = "Changed"
    await assert_manifest_snapshot(session, path, update=True)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["tools"][0]["description"] == "Changed"


@pytest.mark.asyncio
async def test_assert_manifest_cli_update_flag(tmp_path: Path) -> None:
    path = tmp_path / "m.snap"
    session = _FakeSession(
        tools=[{"name": "echo", "description": "Echo", "inputSchema": {"type": "object"}}]
    )
    await assert_manifest_snapshot(session, path)
    session._tools[0]["description"] = "via-cli"
    token = set_cli_update_snapshots(True)
    try:
        await assert_manifest_snapshot(session, path)
    finally:
        reset_cli_update_snapshots(token)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["tools"][0]["description"] == "via-cli"


@pytest.mark.asyncio
async def test_assert_manifest_non_dict_stored(tmp_path: Path) -> None:
    path = tmp_path / "m.snap"
    path.write_text(json.dumps(["not", "a", "dict"]), encoding="utf-8")
    session = _FakeSession(tools=[{"name": "echo", "description": "e", "inputSchema": {}}])
    with pytest.raises(MCPAssertionError, match="rug-pull"):
        await assert_manifest_snapshot(session, path)


# ---------------------------------------------------------------------------
# Config / policy
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_configured_manifest_gate_disabled_and_none() -> None:
    session = _FakeSession()
    assert await run_configured_manifest_gate(session, None) is None
    assert await run_configured_manifest_gate(session, ManifestGatePolicy(enabled=False)) is None


@pytest.mark.asyncio
async def test_run_configured_manifest_gate_enabled(tmp_path: Path) -> None:
    path = tmp_path / "m.snap"
    session = _FakeSession(
        tools=[{"name": "echo", "description": "e", "inputSchema": {"type": "object"}}]
    )
    pol = ManifestGatePolicy(enabled=True, path=str(path))
    out = await run_configured_manifest_gate(session, pol, protocol_version="v1")
    assert out is not None
    assert path.is_file()


def test_parse_and_evaluate() -> None:
    pol = parse_manifest_gate_policy({"enabled": True, "path": "m.snap"})
    assert pol.enabled is True
    assert pol.path == "m.snap"
    assert parse_manifest_gate_policy(None).enabled is False
    assert evaluate_manifest_gate_error(ValueError("x")) == "x"


def test_load_config_manifest_gate(tmp_path: Path) -> None:
    cfg = tmp_path / "mcp-test.yaml"
    cfg.write_text(
        "server:\n  command: python -m server\n"
        "manifest_gate:\n  enabled: true\n  path: snaps/m.snap\n",
        encoding="utf-8",
    )
    loaded = load_config(_ns(config=str(cfg)))
    assert loaded.manifest_gate.enabled is True
    assert loaded.manifest_gate.path == "snaps/m.snap"


def test_validate_manifest_gate_errors(tmp_path: Path) -> None:
    p = tmp_path / "c.yaml"
    p.write_text(
        "server:\n  command: x\nmanifest_gate:\n  nope: 1\n",
        encoding="utf-8",
    )
    errs = validate_config_file(p)
    assert any("manifest_gate" in e.message for e in errs)

    p2 = tmp_path / "c2.yaml"
    p2.write_text("server:\n  command: x\nmanifest_gate: []\n", encoding="utf-8")
    errs2 = validate_config_file(p2)
    assert any("must be a mapping" in e.message for e in errs2)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_manifest_cli_show_update_check(tmp_path: Path) -> None:
    session = _FakeSession(
        tools=[{"name": "echo", "description": "e", "inputSchema": {"type": "object"}}]
    )
    server = MagicMock(spec=ManagedServer)
    server.session = session
    server.capabilities = {"tools": {}}
    server.init_result = SimpleNamespace(protocolVersion="2025-03-26")

    snap = tmp_path / "__snapshots__" / "mcp_manifest.snap"
    cfg = HarnessConfig(server_command="echo")

    with (
        patch("mcp_test_harness.config.load_config", return_value=cfg),
        patch("mcp_test_harness.lifecycle.ServerLifecycleManager") as lm_cls,
    ):
        lm = lm_cls.return_value
        lm.start = AsyncMock(return_value=server)
        lm.shutdown = AsyncMock()
        lm_cls.protocol_version_from_init = MagicMock(return_value="2025-03-26")

        assert await run_manifest_async(["show", "--dir", str(tmp_path), "--path", str(snap)]) == 0
        assert await run_manifest_async(
            ["update", "--dir", str(tmp_path), "--path", str(snap)]
        ) == 0
        assert snap.is_file()
        assert await run_manifest_async(["check", "--dir", str(tmp_path), "--path", str(snap)]) == 0

        session._tools.append(
            {"name": "evil", "description": "x", "inputSchema": {"type": "object"}}
        )
        assert await run_manifest_async(["check", "--dir", str(tmp_path), "--path", str(snap)]) == 1


@pytest.mark.asyncio
async def test_manifest_cli_relative_path_and_startup_error(tmp_path: Path) -> None:
    cfg = HarnessConfig(server_command="echo")
    with (
        patch("mcp_test_harness.config.load_config", return_value=cfg),
        patch("mcp_test_harness.lifecycle.ServerLifecycleManager") as lm_cls,
    ):
        lm = lm_cls.return_value
        lm.start = AsyncMock(side_effect=StartupError("nope"))
        lm.shutdown = AsyncMock()
        code = await run_manifest_async(
            ["check", "--dir", str(tmp_path), "--path", "rel.snap"]
        )
        assert code == 1


@pytest.mark.asyncio
async def test_manifest_cli_load_config_system_exit() -> None:
    with patch(
        "mcp_test_harness.config.load_config",
        side_effect=SystemExit(2),
    ):
        assert await run_manifest_async(["show", "--server-command", "x"]) == 2


def test_run_manifest_sync_wrapper(tmp_path: Path) -> None:
    cfg = HarnessConfig(server_command="echo")
    session = _FakeSession()
    server = MagicMock(spec=ManagedServer)
    server.session = session
    server.capabilities = {}
    server.init_result = None
    with (
        patch("mcp_test_harness.config.load_config", return_value=cfg),
        patch("mcp_test_harness.lifecycle.ServerLifecycleManager") as lm_cls,
    ):
        lm = lm_cls.return_value
        lm.start = AsyncMock(return_value=server)
        lm.shutdown = AsyncMock()
        lm_cls.protocol_version_from_init = MagicMock(return_value="")
        assert run_manifest(["show", "--dir", str(tmp_path)]) == 0


def test_cli_main_dispatches_manifest() -> None:
    from mcp_test_harness.cli import main

    with patch("mcp_test_harness.manifest_gate.run_manifest", return_value=0) as rm:
        assert main(["manifest", "show"]) == 0
        rm.assert_called_once_with(["show"])


# ---------------------------------------------------------------------------
# Scheduler integration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scheduler_manifest_gate_fail_fast() -> None:
    async def _pass():
        pass

    tc = HarnessCase(
        name="test_a",
        module_path=Path("test_a.py"),
        func=_pass,
        markers={},
        is_async=True,
    )
    snap = Path("unused.snap")
    config = HarnessConfig(
        server_command="echo",
        schema_validation=False,
        manifest_gate=ManifestGatePolicy(enabled=True, path=str(snap)),
    )
    server = ManagedServer(
        process=None,
        session=_FakeSession(
            tools=[{"name": "echo", "description": "e", "inputSchema": {}}]
        ),
        transport=MagicMock(),
        capabilities={"tools": {}},
        init_result=SimpleNamespace(protocolVersion="v1"),
    )

    with (
        patch("mcp_test_harness.scheduler.ServerLifecycleManager") as lm_cls,
        patch(
            "mcp_test_harness.scheduler.run_configured_manifest_gate",
            new_callable=AsyncMock,
            side_effect=MCPAssertionError("rug-pull: tools added: evil"),
        ),
        patch(
            "mcp_test_harness.scheduler.capture_advertised_inventory",
            new_callable=AsyncMock,
        ),
        patch("mcp_test_harness.scheduler.CaseExecutor") as mock_exec_cls,
        patch("mcp_test_harness.scheduler.FixtureManager") as mock_fm,
        patch("mcp_test_harness.scheduler.register_builtin_fixtures"),
        patch("mcp_test_harness.scheduler.register_decorated_fixtures"),
    ):
        lm = lm_cls.return_value
        lm.start = AsyncMock(return_value=server)
        lm.shutdown = AsyncMock()
        lm.start_monitor = MagicMock()
        lm_cls.protocol_version_from_init = MagicMock(return_value="v1")
        mock_fm.return_value.teardown = AsyncMock(return_value=[])
        exec_instance = mock_exec_cls.return_value
        exec_instance.execute = AsyncMock()

        sched = HarnessScheduler()
        run = await sched.run_sequential([tc], config, fail_fast=True)

    assert any(
        r.name == "manifest_gate" and r.status == CaseStatus.FAILED for r in run.test_results
    )
    assert any(r.status == CaseStatus.SKIPPED for r in run.test_results)
    exec_instance.execute.assert_not_called()


@pytest.mark.asyncio
async def test_scheduler_parallel_manifest_gate_sets_fail_stop() -> None:
    async def _pass():
        pass

    t1 = HarnessCase(
        name="test_a",
        module_path=Path("m.py"),
        func=_pass,
        markers={},
        is_async=True,
    )
    t2 = HarnessCase(
        name="test_b",
        module_path=Path("m.py"),
        func=_pass,
        markers={},
        is_async=True,
    )
    config = HarnessConfig(
        server_command="echo",
        schema_validation=False,
        manifest_gate=ManifestGatePolicy(enabled=True, path="m.snap"),
    )
    server = ManagedServer(
        process=None,
        session=_FakeSession(),
        transport=MagicMock(),
        capabilities={"tools": {}},
        init_result=SimpleNamespace(protocolVersion="v1"),
    )

    with (
        patch("mcp_test_harness.scheduler.ServerLifecycleManager") as lm_cls,
        patch(
            "mcp_test_harness.scheduler.run_configured_manifest_gate",
            new_callable=AsyncMock,
            side_effect=MCPAssertionError("rug-pull"),
        ),
        patch(
            "mcp_test_harness.scheduler.capture_advertised_inventory",
            new_callable=AsyncMock,
        ),
        patch("mcp_test_harness.scheduler.CaseExecutor") as mock_exec_cls,
        patch("mcp_test_harness.scheduler.FixtureManager") as mock_fm,
        patch("mcp_test_harness.scheduler.register_builtin_fixtures"),
        patch("mcp_test_harness.scheduler.register_decorated_fixtures"),
    ):
        lm = lm_cls.return_value
        lm.start = AsyncMock(return_value=server)
        lm.shutdown = AsyncMock()
        lm.start_monitor = MagicMock()
        lm_cls.protocol_version_from_init = MagicMock(return_value="v1")
        mock_fm.return_value.teardown = AsyncMock(return_value=[])
        mock_exec_cls.return_value.execute = AsyncMock(
            return_value=CaseResult(
                name="x",
                module="m.py",
                status=CaseStatus.PASSED,
                duration_ms=1.0,
            )
        )

        run = await HarnessScheduler().run_parallel(
            [t1, t2], config, workers=1, fail_fast=True
        )

    assert any(r.name == "manifest_gate" for r in run.test_results)
    assert any(r.status == CaseStatus.SKIPPED for r in run.test_results)
