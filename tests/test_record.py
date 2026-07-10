"""Tests for RFC-001 mcp-test record."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_test_harness.cli import main
from mcp_test_harness.record import (
    load_cassette,
    render_recorded_module,
    run_record,
    run_record_async,
    write_snapshots_for_calls,
)


def test_load_cassette_list_and_object(tmp_path: Path) -> None:
    p = tmp_path / "c.json"
    p.write_text(
        json.dumps(
            {
                "calls": [
                    {"tool": "echo", "arguments": {"text": "hi"}, "response": {"ok": True}},
                    "not-a-dict",
                    {"tool": "", "name": ""},
                    {"tool": "bad", "arguments": "not-a-dict"},
                    {"tool": "err", "arguments": {}, "error": "boom"},
                ]
            }
        ),
        encoding="utf-8",
    )
    calls = load_cassette(p)
    assert calls[0]["tool"] == "echo"
    assert calls[0]["arguments"] == {"text": "hi"}
    assert any(c["tool"] == "bad" and c["arguments"] == {} for c in calls)
    assert any(c["tool"] == "err" and c.get("error") == "boom" for c in calls)

    p2 = tmp_path / "list.json"
    p2.write_text(json.dumps([{"tool": "a", "args": {"x": 1}}]), encoding="utf-8")
    assert load_cassette(p2)[0]["arguments"] == {"x": 1}


def test_load_cassette_errors(tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
    p.write_text("null", encoding="utf-8")
    with pytest.raises(ValueError):
        load_cassette(p)
    p.write_text(json.dumps({"calls": "x"}), encoding="utf-8")
    with pytest.raises(ValueError):
        load_cassette(p)


def test_render_recorded_module_and_duplicates() -> None:
    src = render_recorded_module(
        [
            {"tool": "echo", "arguments": {"text": "a"}, "response": {"r": 1}},
            {"tool": "echo", "arguments": {"text": "b"}, "response": {"r": 2}},
            {"tool": "fail", "arguments": {}, "error": "boom"},
        ]
    )
    assert "test_recorded_echo" in src
    assert "test_recorded_echo_2" in src
    assert "assert_snapshot" in src
    assert "test_recorded_fail" not in src  # transport-only failure skipped
    assert '@marker(tags=["smoke", "recorded"])' in src
    # BUG H: docstring must close with three quotes (valid Python)
    assert '"""Recorded happy-path for tool ``echo``."""' in src
    compile(src, "<recorded>", "exec")


def test_render_recorded_module_iserror_emits_rejects() -> None:
    """MCP isError responses become assert_tool_rejects, not false happy-paths."""
    src = render_recorded_module(
        [
            {
                "tool": "boom",
                "arguments": {},
                "response": {"isError": True, "content": [{"type": "text", "text": "nope"}]},
                "error": "MCP tool returned isError=true",
            },
            {"tool": "echo", "arguments": {"text": "hi"}, "response": {"ok": True}},
        ]
    )
    assert "assert_tool_rejects" in src
    assert "test_recorded_boom_rejects" in src
    assert "test_recorded_echo" in src
    assert "assert_tool_call" in src
    assert "happy-path for tool ``boom``" not in src
    compile(src, "<recorded>", "exec")


def test_render_recorded_module_empty() -> None:
    src = render_recorded_module([{"tool": "x", "arguments": {}, "error": "e"}])
    assert "test_recorded_no_calls" in src


def test_write_snapshots_for_calls(tmp_path: Path) -> None:
    out = tmp_path / "tests" / "test_rec.py"
    out.parent.mkdir(parents=True)
    out.write_text("# placeholder\n", encoding="utf-8")
    n = write_snapshots_for_calls(
        out,
        [
            {"tool": "echo", "arguments": {}, "response": {"content": [{"type": "text", "text": "hi"}]}},
            {"tool": "echo", "arguments": {}, "response": {"content": []}},
            {"tool": "skip", "arguments": {}, "error": "x"},
            {"tool": "nosnap", "arguments": {}},
        ],
    )
    assert n == 2
    snap_dir = out.parent / "__snapshots__"
    assert (snap_dir / "recorded_echo.snap").is_file()
    assert (snap_dir / "recorded_echo_2.snap").is_file()


def test_run_record_from_json_offline(tmp_path: Path) -> None:
    cassette = tmp_path / "cass.json"
    cassette.write_text(
        json.dumps(
            {
                "calls": [
                    {
                        "tool": "echo",
                        "arguments": {"text": "hi"},
                        "response": {"ok": True},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "out" / "test_mcp_recorded.py"
    session = tmp_path / "session.json"
    code = asyncio.run(
        run_record_async(
            [
                "--from-json",
                str(cassette),
                "--out",
                str(out),
                "--force",
                "--session-json",
                str(session),
                "--server-command",
                "python -c pass",
            ]
        )
    )
    assert code == 0
    assert out.is_file()
    assert "test_recorded_echo" in out.read_text(encoding="utf-8")
    assert (out.parent / "__snapshots__" / "recorded_echo.snap").is_file()
    assert session.is_file()


def test_run_record_refuse_overwrite(tmp_path: Path) -> None:
    out = tmp_path / "t.py"
    out.write_text("exists", encoding="utf-8")
    cassette = tmp_path / "c.json"
    cassette.write_text(
        json.dumps({"calls": [{"tool": "a", "arguments": {}, "response": {}}]}),
        encoding="utf-8",
    )
    code = asyncio.run(
        run_record_async(
            ["--from-json", str(cassette), "--out", str(out), "--server-command", "x"]
        )
    )
    assert code == 2


def test_run_record_missing_cassette(tmp_path: Path) -> None:
    code = asyncio.run(
        run_record_async(
            [
                "--from-json",
                str(tmp_path / "missing.json"),
                "--out",
                str(tmp_path / "o.py"),
                "--server-command",
                "x",
            ]
        )
    )
    assert code == 2


def test_run_record_invalid_cassette(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{", encoding="utf-8")
    code = asyncio.run(
        run_record_async(
            [
                "--from-json",
                str(bad),
                "--out",
                str(tmp_path / "o.py"),
                "--force",
                "--server-command",
                "x",
            ]
        )
    )
    assert code == 2


def test_run_record_live_mocked(tmp_path: Path) -> None:
    tool = MagicMock()
    tool.name = "echo"
    tool.inputSchema = {
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
    }

    session = MagicMock()
    session.list_tools = AsyncMock(return_value=MagicMock(tools=[tool]))
    session.call_tool = AsyncMock(
        return_value=MagicMock(content=[{"type": "text", "text": "hi"}])
    )

    server = MagicMock()
    server.session = session

    lifecycle = MagicMock()
    lifecycle.start = AsyncMock(return_value=server)
    lifecycle.shutdown = AsyncMock()

    out = tmp_path / "test_rec.py"
    with (
        patch("mcp_test_harness.lifecycle.ServerLifecycleManager", return_value=lifecycle),
        patch("mcp_test_harness.config.load_config") as lc,
    ):
        cfg = MagicMock()
        cfg.server_command = "python srv.py"
        lc.return_value = cfg
        code = asyncio.run(
            run_record_async(
                [
                    "--server-command",
                    "python srv.py",
                    "--out",
                    str(out),
                    "--force",
                    "--max-tools",
                    "1",
                ]
            )
        )
    assert code == 0
    text = out.read_text(encoding="utf-8")
    assert "test_recorded_echo" in text
    session.call_tool.assert_awaited()


def test_run_record_live_tool_error(tmp_path: Path) -> None:
    tool = MagicMock()
    tool.name = "boom"
    tool.inputSchema = {}

    session = MagicMock()
    session.list_tools = AsyncMock(return_value=MagicMock(tools=[tool]))
    session.call_tool = AsyncMock(side_effect=RuntimeError("nope"))

    server = MagicMock()
    server.session = session
    lifecycle = MagicMock()
    lifecycle.start = AsyncMock(return_value=server)
    lifecycle.shutdown = AsyncMock()

    out = tmp_path / "t.py"
    with (
        patch("mcp_test_harness.lifecycle.ServerLifecycleManager", return_value=lifecycle),
        patch("mcp_test_harness.config.load_config") as lc,
    ):
        lc.return_value = MagicMock(server_command="x")
        code = asyncio.run(
            run_record_async(["--server-command", "x", "--out", str(out), "--force"])
        )
    assert code == 0
    assert "test_recorded_no_calls" in out.read_text(encoding="utf-8")


def test_run_record_startup_error() -> None:
    from mcp_test_harness.lifecycle import StartupError

    lifecycle = MagicMock()
    lifecycle.start = AsyncMock(side_effect=StartupError("down"))
    lifecycle.shutdown = AsyncMock()
    with (
        patch("mcp_test_harness.lifecycle.ServerLifecycleManager", return_value=lifecycle),
        patch("mcp_test_harness.config.load_config") as lc,
    ):
        lc.return_value = MagicMock(server_command="x")
        with pytest.raises(SystemExit) as ei:
            asyncio.run(
                run_record_async(
                    ["--server-command", "x", "--out", "tests/tmp_recorded.py", "--force"]
                )
            )
    assert ei.value.code == 1


def test_run_record_filter_tools(tmp_path: Path) -> None:
    cassette = tmp_path / "c.json"
    cassette.write_text(
        json.dumps(
            {
                "calls": [
                    {"tool": "keep", "arguments": {}, "response": {"a": 1}},
                    {"tool": "drop", "arguments": {}, "response": {"b": 2}},
                ]
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "o.py"
    code = asyncio.run(
        run_record_async(
            [
                "--from-json",
                str(cassette),
                "--out",
                str(out),
                "--force",
                "--tools",
                "keep",
                "--no-snapshots",
                "--server-command",
                "x",
            ]
        )
    )
    assert code == 0
    text = out.read_text(encoding="utf-8")
    assert "test_recorded_keep" in text
    assert "test_recorded_drop" not in text


def test_run_record_fill_missing_responses(tmp_path: Path) -> None:
    cassette = tmp_path / "c.json"
    cassette.write_text(
        json.dumps({"calls": [{"tool": "echo", "arguments": {"text": "z"}}]}),
        encoding="utf-8",
    )
    session = MagicMock()
    session.call_tool = AsyncMock(return_value={"ok": True})
    server = MagicMock(session=session)
    lifecycle = MagicMock()
    lifecycle.start = AsyncMock(return_value=server)
    lifecycle.shutdown = AsyncMock()
    out = tmp_path / "o.py"
    with (
        patch("mcp_test_harness.lifecycle.ServerLifecycleManager", return_value=lifecycle),
        patch("mcp_test_harness.config.load_config") as lc,
    ):
        lc.return_value = MagicMock(server_command="python x")
        code = asyncio.run(
            run_record_async(
                [
                    "--from-json",
                    str(cassette),
                    "--out",
                    str(out),
                    "--force",
                    "--server-command",
                    "python x",
                ]
            )
        )
    assert code == 0
    session.call_tool.assert_awaited()
    assert (out.parent / "__snapshots__" / "recorded_echo.snap").is_file()


def test_run_record_load_config_exit() -> None:
    with patch("mcp_test_harness.config.load_config", side_effect=SystemExit(2)):
        assert (
            asyncio.run(
                run_record_async(["--server-command", "x", "--out", "t.py", "--force"])
            )
            == 2
        )


def test_run_record_sync_entry() -> None:
    with patch("mcp_test_harness.record.run_record_async", new_callable=AsyncMock) as m:
        m.return_value = 0
        assert run_record(["--server-command", "x"]) == 0


def test_main_dispatches_record() -> None:
    with patch("mcp_test_harness.record.run_record", return_value=0) as rr:
        assert main(["record", "--server-command", "x"]) == 0
    rr.assert_called_once_with(["--server-command", "x"])


def test_fill_missing_noop_when_complete() -> None:
    from mcp_test_harness.record import _fill_missing_responses

    calls = [{"tool": "a", "arguments": {}, "response": {"x": 1}}]
    out = asyncio.run(_fill_missing_responses(MagicMock(server_command="x"), calls))
    assert out is calls


def test_fill_missing_startup_and_call_errors() -> None:
    from mcp_test_harness.lifecycle import StartupError
    from mcp_test_harness.record import _fill_missing_responses

    lifecycle = MagicMock()
    lifecycle.start = AsyncMock(side_effect=StartupError("down"))
    lifecycle.shutdown = AsyncMock()
    with patch("mcp_test_harness.lifecycle.ServerLifecycleManager", return_value=lifecycle):
        with pytest.raises(SystemExit):
            asyncio.run(
                _fill_missing_responses(
                    MagicMock(server_command="x"),
                    [{"tool": "a", "arguments": {}}],
                )
            )

    session = MagicMock()
    session.call_tool = AsyncMock(side_effect=RuntimeError("fail"))
    server = MagicMock(session=session)
    lifecycle2 = MagicMock()
    lifecycle2.start = AsyncMock(return_value=server)
    lifecycle2.shutdown = AsyncMock()
    calls = [{"tool": "a", "arguments": {}}]
    with patch("mcp_test_harness.lifecycle.ServerLifecycleManager", return_value=lifecycle2):
        out = asyncio.run(_fill_missing_responses(MagicMock(server_command="x"), calls))
    assert out[0].get("error") == "fail"


def test_run_record_max_tools_cassette(tmp_path: Path) -> None:
    cassette = tmp_path / "c.json"
    cassette.write_text(
        json.dumps(
            {
                "calls": [
                    {"tool": "a", "arguments": {}, "response": {"a": 1}},
                    {"tool": "b", "arguments": {}, "response": {"b": 2}},
                ]
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "o.py"
    code = asyncio.run(
        run_record_async(
            [
                "--from-json",
                str(cassette),
                "--out",
                str(out),
                "--force",
                "--max-tools",
                "1",
                "--no-snapshots",
                "--server-command",
                "x",
            ]
        )
    )
    assert code == 0
    text = out.read_text(encoding="utf-8")
    assert "test_recorded_a" in text
    assert "test_recorded_b" not in text


def test_run_record_offline_missing_response_no_fill(tmp_path: Path) -> None:
    cassette = tmp_path / "c.json"
    cassette.write_text(
        json.dumps({"calls": [{"tool": "echo", "arguments": {"text": "z"}}]}),
        encoding="utf-8",
    )
    out = tmp_path / "o.py"
    with patch("mcp_test_harness.config.load_config") as lc:
        lc.return_value = MagicMock(server_command="")
        code = asyncio.run(
            run_record_async(
                [
                    "--from-json",
                    str(cassette),
                    "--out",
                    str(out),
                    "--force",
                    "--no-snapshots",
                ]
            )
        )
    assert code == 0
    assert "test_recorded_echo" in out.read_text(encoding="utf-8")


def test_run_record_skips_unknown_tools(tmp_path: Path) -> None:
    t_ok = MagicMock()
    t_ok.name = "ok"
    t_ok.inputSchema = {}
    t_bad = MagicMock()
    t_bad.name = "unknown"
    t_bad.inputSchema = {}
    # force _tool_name unknown via empty name
    t_empty = MagicMock()
    t_empty.name = ""
    t_empty.inputSchema = {}

    session = MagicMock()
    session.list_tools = AsyncMock(return_value=MagicMock(tools=[t_empty, t_ok]))
    session.call_tool = AsyncMock(return_value={"ok": 1})
    server = MagicMock(session=session)
    lifecycle = MagicMock()
    lifecycle.start = AsyncMock(return_value=server)
    lifecycle.shutdown = AsyncMock()
    out = tmp_path / "o.py"
    with (
        patch("mcp_test_harness.lifecycle.ServerLifecycleManager", return_value=lifecycle),
        patch("mcp_test_harness.config.load_config") as lc,
        patch("mcp_test_harness.record._tool_name", side_effect=lambda t: getattr(t, "name", None) or "unknown"),
    ):
        lc.return_value = MagicMock(server_command="x")
        code = asyncio.run(
            run_record_async(
                ["--server-command", "x", "--out", str(out), "--force", "--no-snapshots"]
            )
        )
    assert code == 0
    assert "test_recorded_ok" in out.read_text(encoding="utf-8")


def test_run_record_tools_filter_live(tmp_path: Path) -> None:
    t1 = MagicMock(name="keep")
    t1.name = "keep"
    t1.inputSchema = {}
    t2 = MagicMock()
    t2.name = "drop"
    t2.inputSchema = {}
    session = MagicMock()
    session.list_tools = AsyncMock(return_value=MagicMock(tools=[t1, t2]))
    session.call_tool = AsyncMock(return_value={"ok": 1})
    server = MagicMock(session=session)
    lifecycle = MagicMock()
    lifecycle.start = AsyncMock(return_value=server)
    lifecycle.shutdown = AsyncMock()
    out = tmp_path / "o.py"
    with (
        patch("mcp_test_harness.lifecycle.ServerLifecycleManager", return_value=lifecycle),
        patch("mcp_test_harness.config.load_config") as lc,
    ):
        lc.return_value = MagicMock(server_command="x")
        code = asyncio.run(
            run_record_async(
                [
                    "--server-command",
                    "x",
                    "--out",
                    str(out),
                    "--force",
                    "--tools",
                    "keep",
                    "--no-snapshots",
                ]
            )
        )
    assert code == 0
    assert "test_recorded_keep" in out.read_text(encoding="utf-8")
    assert session.call_tool.await_count == 1
