"""Tests for ``mcp-test doctor`` (health check without test files)."""

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_test_harness.config import HarnessConfig
from mcp_test_harness.doctor import _doctor_async, run_doctor


def test_run_doctor_no_server_exits_2(capsys):
    """No server command -> load_config exit 2."""
    with patch("mcp_test_harness.doctor.load_config", side_effect=SystemExit(2)):
        code = run_doctor(["--server-command", ""])
    assert code == 2


@pytest.mark.asyncio
async def test_doctor_happy_path_schema_off():
    """Start/shutdown, list tools/resources/prompts, skip schema when disabled."""
    cfg = replace(
        HarnessConfig(server_command="echo mcp", schema_validation=False), timeout=5.0
    )

    mock_server = MagicMock()
    mock_server.init_result = SimpleNamespace(protocolVersion="2025-03-26")
    mock_server.capabilities = {"tools": {}}
    se = MagicMock()
    se.list_tools = AsyncMock(
        return_value=SimpleNamespace(tools=[SimpleNamespace(name="echo")])
    )
    se.list_resources = AsyncMock(return_value=SimpleNamespace(resources=[]))
    se.list_prompts = AsyncMock(return_value=SimpleNamespace(prompts=[]))
    mock_server.session = se

    with patch("mcp_test_harness.doctor.ServerLifecycleManager") as M:
        inst = M.return_value
        inst.start = AsyncMock(return_value=mock_server)
        inst.shutdown = AsyncMock()
        code = await _doctor_async(cfg)

    assert code == 0
    inst.shutdown.assert_awaited_once()


@pytest.mark.asyncio
async def test_doctor_schema_fail_returns_1():
    from mcp_test_harness.models import SchemaViolation

    cfg = HarnessConfig(server_command="x", schema_validation=True)
    mock_server = MagicMock()
    mock_server.init_result = SimpleNamespace()
    mock_server.capabilities = {}
    mock_server.session = MagicMock()
    mock_server.session.list_tools = AsyncMock(return_value=SimpleNamespace(tools=[]))
    mock_server.session.list_resources = AsyncMock(return_value=SimpleNamespace(resources=[]))
    mock_server.session.list_prompts = AsyncMock(return_value=SimpleNamespace(prompts=[]))

    viol = [SchemaViolation(json_path="x", expected_type="t", actual_value=1, message="bad")]

    with (
        patch("mcp_test_harness.doctor.ServerLifecycleManager") as M,
        patch(
            "mcp_test_harness.schema.validate_mcp_server_after_connect",
            new=AsyncMock(return_value=viol),
        ),
    ):
        M.return_value.start = AsyncMock(return_value=mock_server)
        M.return_value.shutdown = AsyncMock()
        code = await _doctor_async(cfg)

    assert code == 1


@pytest.mark.asyncio
async def test_doctor_startup_error_returns_1(capsys):
    cfg = HarnessConfig(server_command="x")
    with patch("mcp_test_harness.doctor.ServerLifecycleManager") as M:
        M.return_value.start = AsyncMock(side_effect=Exception("boom"))
        # _doctor_async catches StartupError, so make scheduler raise that type
        from mcp_test_harness.lifecycle import StartupError

        M.return_value.start = AsyncMock(side_effect=StartupError("failed to start"))
        code = await _doctor_async(cfg)
    assert code == 1
    assert "failed to start" in capsys.readouterr().err


@pytest.mark.asyncio
async def test_doctor_list_api_fallbacks_and_warnings(capsys):
    cfg = HarnessConfig(server_command="x", schema_validation=False)
    mock_server = MagicMock()
    mock_server.init_result = SimpleNamespace(protocol_version="2026-01-01")
    mock_server.capabilities = {f"k{i}": i for i in range(15)}
    se = MagicMock()
    # list_tools/list_prompts return plain lists (fallback branch), resources raises (warning branch)
    se.list_tools = AsyncMock(return_value=[SimpleNamespace(name="t1"), "tool2"])
    se.list_resources = AsyncMock(side_effect=RuntimeError("res failed"))
    se.list_prompts = AsyncMock(return_value=["p1"])
    mock_server.session = se

    with patch("mcp_test_harness.doctor.ServerLifecycleManager") as M:
        M.return_value.start = AsyncMock(return_value=mock_server)
        M.return_value.shutdown = AsyncMock()
        code = await _doctor_async(cfg)

    out = capsys.readouterr()
    assert code == 0
    assert "Capabilities:" in out.out
    assert "t1" in out.out
    assert "Schema validation: skipped" in out.out


@pytest.mark.asyncio
async def test_doctor_resources_list_fallback_branch():
    cfg = HarnessConfig(server_command="x", schema_validation=False)
    mock_server = MagicMock()
    mock_server.init_result = SimpleNamespace(protocolVersion="2025-03-26")
    mock_server.capabilities = {}
    se = MagicMock()
    se.list_tools = AsyncMock(return_value=SimpleNamespace(tools=[]))
    # plain list -> fallback branch in doctor.py
    se.list_resources = AsyncMock(return_value=["r1"])
    se.list_prompts = AsyncMock(return_value=SimpleNamespace(prompts=[]))
    mock_server.session = se
    with patch("mcp_test_harness.doctor.ServerLifecycleManager") as M:
        M.return_value.start = AsyncMock(return_value=mock_server)
        M.return_value.shutdown = AsyncMock()
        code = await _doctor_async(cfg)
    assert code == 0


@pytest.mark.asyncio
async def test_doctor_warning_when_all_lists_fail(capsys):
    cfg = HarnessConfig(server_command="x", schema_validation=False)
    mock_server = MagicMock()
    mock_server.init_result = SimpleNamespace()
    mock_server.capabilities = {}
    se = MagicMock()
    se.list_tools = AsyncMock(side_effect=RuntimeError("lt fail"))
    se.list_resources = AsyncMock(side_effect=RuntimeError("lr fail"))
    se.list_prompts = AsyncMock(side_effect=RuntimeError("lp fail"))
    mock_server.session = se
    with patch("mcp_test_harness.doctor.ServerLifecycleManager") as M:
        M.return_value.start = AsyncMock(return_value=mock_server)
        M.return_value.shutdown = AsyncMock()
        code = await _doctor_async(cfg)
    err = capsys.readouterr().err
    assert code == 0
    assert "Warning: list_tools" in err
    assert "Warning: list_resources" in err
    assert "Warning: list_prompts" in err


@pytest.mark.asyncio
async def test_doctor_tools_more_than_twenty_prints_more_line(capsys):
    cfg = HarnessConfig(server_command="x", schema_validation=False)
    mock_server = MagicMock()
    mock_server.init_result = SimpleNamespace(protocolVersion="2025-03-26")
    mock_server.capabilities = {}
    tools = [SimpleNamespace(name=f"t{i}") for i in range(25)]
    se = MagicMock()
    se.list_tools = AsyncMock(return_value=SimpleNamespace(tools=tools))
    se.list_resources = AsyncMock(return_value=SimpleNamespace(resources=[]))
    se.list_prompts = AsyncMock(return_value=SimpleNamespace(prompts=[]))
    mock_server.session = se
    with patch("mcp_test_harness.doctor.ServerLifecycleManager") as M:
        M.return_value.start = AsyncMock(return_value=mock_server)
        M.return_value.shutdown = AsyncMock()
        code = await _doctor_async(cfg)
    assert code == 0
    assert "more" in capsys.readouterr().out


@pytest.mark.asyncio
async def test_doctor_schema_ok_path(capsys):
    cfg = HarnessConfig(server_command="x", schema_validation=True)
    mock_server = MagicMock()
    mock_server.init_result = SimpleNamespace(protocolVersion="2025-03-26")
    mock_server.capabilities = {}
    se = MagicMock()
    se.list_tools = AsyncMock(return_value=SimpleNamespace(tools=[]))
    se.list_resources = AsyncMock(return_value=SimpleNamespace(resources=[]))
    se.list_prompts = AsyncMock(return_value=SimpleNamespace(prompts=[]))
    mock_server.session = se
    with (
        patch("mcp_test_harness.doctor.ServerLifecycleManager") as M,
        patch(
            "mcp_test_harness.schema.validate_mcp_server_after_connect",
            new=AsyncMock(return_value=[]),
        ),
    ):
        M.return_value.start = AsyncMock(return_value=mock_server)
        M.return_value.shutdown = AsyncMock()
        code = await _doctor_async(cfg)
    assert code == 0
    assert "Schema: OK" in capsys.readouterr().out


@pytest.mark.asyncio
async def test_doctor_schema_many_violations_prints_and_more(capsys):
    from mcp_test_harness.models import SchemaViolation

    cfg = HarnessConfig(server_command="x", schema_validation=True)
    mock_server = MagicMock()
    mock_server.init_result = SimpleNamespace(protocolVersion="2025-03-26")
    mock_server.capabilities = {}
    se = MagicMock()
    se.list_tools = AsyncMock(return_value=SimpleNamespace(tools=[]))
    se.list_resources = AsyncMock(return_value=SimpleNamespace(resources=[]))
    se.list_prompts = AsyncMock(return_value=SimpleNamespace(prompts=[]))
    mock_server.session = se
    viol = [
        SchemaViolation(json_path=f"$.{i}", expected_type="x", actual_value=None, message=f"m{i}")
        for i in range(25)
    ]
    with (
        patch("mcp_test_harness.doctor.ServerLifecycleManager") as M,
        patch(
            "mcp_test_harness.schema.validate_mcp_server_after_connect",
            new=AsyncMock(return_value=viol),
        ),
    ):
        M.return_value.start = AsyncMock(return_value=mock_server)
        M.return_value.shutdown = AsyncMock()
        code = await _doctor_async(cfg)
    out = capsys.readouterr().out
    assert code == 1
    assert "and 5 more" in out


def test_run_doctor_non_int_system_exit_maps_to_2():
    with patch("mcp_test_harness.doctor.load_config", side_effect=SystemExit("bad")):
        assert run_doctor([]) == 2


def test_run_doctor_no_schema_flag_disables_schema():
    with patch("mcp_test_harness.doctor.load_config", return_value=HarnessConfig(server_command="x")):
        with patch("mcp_test_harness.doctor._doctor_async", return_value=0) as mock_doc:
            code = run_doctor(["--no-schema"])
    assert code == 0
    cfg = mock_doc.call_args.args[0]
    assert cfg.schema_validation is False
