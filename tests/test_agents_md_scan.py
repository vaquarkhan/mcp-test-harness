"""Tests for defensive AGENTS.md / agent-rules hidden-Unicode scan."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcp_test_harness.agents_md_scan import (
    AgentsMdGatePolicy,
    assert_agents_md_clean,
    filter_findings,
    format_findings,
    parse_agents_md_gate_policy,
    resolve_agent_rule_paths,
    run_configured_agents_md_gate,
    run_scan_agents,
    scan_agents_md_paths,
    scan_project_agent_rules,
    scan_text_for_hidden_unicode,
)
from mcp_test_harness.assertions import MCPAssertionError
from mcp_test_harness.config import load_config, validate_config_file


def test_scan_clean_ascii() -> None:
    assert scan_text_for_hidden_unicode("hello AGENTS.md\n") == []


def test_scan_zero_width() -> None:
    text = "approve\u200bthis"
    hits = scan_text_for_hidden_unicode(text, path="AGENTS.md")
    assert len(hits) == 1
    assert hits[0].band == "zero-width"
    assert hits[0].severity == "high"
    assert hits[0].codepoint == "U+200B"
    assert hits[0].line == 1


def test_scan_tags_block_decodes_hint() -> None:
    # U+E0048 'H', U+E0069 'i' — invisible Tags-block smuggling
    # Include language-tag bookends (U+E0001 / U+E007F) skipped by decoder.
    smuggled = chr(0xE0001) + chr(0xE0048) + chr(0xE0069) + chr(0xE007F)
    text = f"Visible rules\n{smuggled}\n"
    hits = scan_text_for_hidden_unicode(text, path="AGENTS.md")
    assert len(hits) == 4
    assert hits[0].band == "unicode-tags"
    assert hits[0].severity == "critical"
    assert any("Hi" in (h.decoded_hint or "") for h in hits)


def test_scan_bidi_override() -> None:
    hits = scan_text_for_hidden_unicode("ok\u202eevil", path="x.md")
    assert any(h.band == "bidi-override" and h.severity == "critical" for h in hits)


def test_scan_bidi_isolate_and_word_joiner() -> None:
    hits = scan_text_for_hidden_unicode("a\u2066b\u2060c", path="x.md")
    bands = {h.band for h in hits}
    assert "bidi-isolate" in bands
    assert "zero-width" in bands


def test_leading_bom_ignored_unless_strict() -> None:
    text = "\ufeff# Title\n"
    assert scan_text_for_hidden_unicode(text) == []
    strict = scan_text_for_hidden_unicode(text, strict=True)
    assert len(strict) == 1
    assert strict[0].severity == "low"
    assert "Leading BOM" in strict[0].detail


def test_mid_file_bom_flagged() -> None:
    text = "# Title\n\ufeffhidden\n"
    hits = scan_text_for_hidden_unicode(text)
    assert len(hits) == 1
    assert hits[0].band == "bom"
    assert hits[0].severity == "medium"
    assert hits[0].line == 2


def test_soft_hyphen_and_multiline_columns() -> None:
    text = "line1\nignore\u00adme\n"
    hits = scan_text_for_hidden_unicode(text, path="AGENTS.md")
    assert len(hits) == 1
    assert hits[0].line == 2
    assert hits[0].column == 7


def test_filter_and_format_findings() -> None:
    hits = scan_text_for_hidden_unicode("a\u200bb\ufeffc")  # high + medium mid? BOM mid
    # "a\u200bb\ufeffc" — ZWSP high, BOM medium
    high = filter_findings(hits, fail_on="high")
    assert all(h.severity in ("high", "critical") for h in high)
    med = filter_findings(hits, fail_on="medium")
    assert len(med) >= len(high)
    blob = format_findings(hits)
    assert "U+200B" in blob


def test_resolve_and_scan_files(tmp_path: Path) -> None:
    clean = tmp_path / "AGENTS.md"
    clean.write_text("# ok\n", encoding="utf-8")
    bad = tmp_path / "CLAUDE.md"
    bad.write_text("x\u200by\n", encoding="utf-8")
    (tmp_path / "skip.txt").write_text("\u200b", encoding="utf-8")
    paths = resolve_agent_rule_paths(tmp_path)
    names = {p.name for p in paths}
    assert names == {"AGENTS.md", "CLAUDE.md"}
    findings = scan_project_agent_rules(tmp_path)
    assert len(findings) == 1
    assert findings[0].band == "zero-width"


def test_resolve_explicit_paths_and_missing(tmp_path: Path) -> None:
    f = tmp_path / "custom.md"
    f.write_text("ok", encoding="utf-8")
    assert resolve_agent_rule_paths(tmp_path, ["custom.md", "nope.md"]) == [f.resolve()]
    assert scan_agents_md_paths([tmp_path / "nope.md"]) == []


def test_resolve_cursor_rules_and_skills(tmp_path: Path) -> None:
    rules = tmp_path / ".cursor" / "rules"
    rules.mkdir(parents=True)
    (rules / "a.mdc").write_text("r", encoding="utf-8")
    (rules / "b.md").write_text("r", encoding="utf-8")
    skill = tmp_path / "skills" / "demo"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("s", encoding="utf-8")
    found = resolve_agent_rule_paths(tmp_path)
    names = {p.name for p in found}
    assert names == {"a.mdc", "b.md", "SKILL.md"}


def test_assert_agents_md_clean_ok_and_fail(tmp_path: Path) -> None:
    p = tmp_path / "AGENTS.md"
    p.write_text("clean\n", encoding="utf-8")
    assert assert_agents_md_clean(p) == []
    p.write_text("bad\u200b\n", encoding="utf-8")
    with pytest.raises(MCPAssertionError, match="hidden Unicode"):
        assert_agents_md_clean(p)
    with pytest.raises(MCPAssertionError):
        assert_agents_md_clean([p])
    # discover under root
    with pytest.raises(MCPAssertionError):
        assert_agents_md_clean(root=tmp_path)


def test_assert_truncates_long_report(tmp_path: Path) -> None:
    # Many findings → truncation branch
    p = tmp_path / "AGENTS.md"
    p.write_text("\u200b" * 40, encoding="utf-8")
    with pytest.raises(MCPAssertionError, match="more"):
        assert_agents_md_clean(p)


def test_parse_policy_and_gate(tmp_path: Path) -> None:
    assert parse_agents_md_gate_policy(None).enabled is False
    assert parse_agents_md_gate_policy({}).enabled is False
    pol = parse_agents_md_gate_policy(
        {
            "enabled": True,
            "paths": "AGENTS.md",
            "fail_on": "high",
            "strict": True,
            "root": str(tmp_path),
        }
    )
    assert pol.enabled and pol.paths == ("AGENTS.md",) and pol.strict
    with pytest.raises(ValueError, match="fail_on"):
        parse_agents_md_gate_policy({"fail_on": "ultra"})

    assert run_configured_agents_md_gate(None) is None
    assert run_configured_agents_md_gate(AgentsMdGatePolicy(enabled=False)) is None

    (tmp_path / "AGENTS.md").write_text("ok\n", encoding="utf-8")
    out = run_configured_agents_md_gate(
        AgentsMdGatePolicy(enabled=True, root=str(tmp_path))
    )
    assert out == []

    (tmp_path / "AGENTS.md").write_text("x\u200by\n", encoding="utf-8")
    with pytest.raises(MCPAssertionError, match="agents_md_gate"):
        run_configured_agents_md_gate(
            AgentsMdGatePolicy(enabled=True, root=str(tmp_path))
        )


def test_load_config_agents_md_gate(tmp_path: Path) -> None:
    cfg = tmp_path / "mcp-test.yaml"
    cfg.write_text(
        "server:\n  command: x\n"
        "agents_md_gate:\n  enabled: true\n  fail_on: critical\n  paths:\n    - AGENTS.md\n",
        encoding="utf-8",
    )
    ns = MagicMock(
        test_path=None,
        version=False,
        list=False,
        watch=False,
        config=str(cfg),
        server_command=None,
        transport=None,
        timeout=None,
        verbose=False,
        parallel=None,
        workers=None,
        report_format=None,
        report_output=None,
        sarif_output=None,
        pr_summary_output=None,
        update_snapshots=None,
        filter_name=None,
        filter_marker=None,
        fail_fast=False,
        last_failed=False,
        pdf_output=None,
        cra_output=None,
    )
    loaded = load_config(ns)
    assert loaded.agents_md_gate.enabled is True
    assert loaded.agents_md_gate.fail_on == "critical"
    assert loaded.agents_md_gate.paths == ("AGENTS.md",)


def test_load_config_agents_md_gate_invalid_fail_on(tmp_path: Path) -> None:
    cfg = tmp_path / "mcp-test.yaml"
    cfg.write_text(
        "server:\n  command: x\nagents_md_gate:\n  fail_on: ultra\n",
        encoding="utf-8",
    )
    ns = MagicMock(
        test_path=None,
        version=False,
        list=False,
        watch=False,
        config=str(cfg),
        server_command=None,
        transport=None,
        timeout=None,
        verbose=False,
        parallel=None,
        workers=None,
        report_format=None,
        report_output=None,
        sarif_output=None,
        pr_summary_output=None,
        update_snapshots=None,
        filter_name=None,
        filter_marker=None,
        fail_fast=False,
        last_failed=False,
        pdf_output=None,
        cra_output=None,
    )
    with pytest.raises(ValueError, match="fail_on"):
        load_config(ns)

    p = tmp_path / "bad.yaml"
    p.write_text("server:\n  command: x\nagents_md_gate: []\n", encoding="utf-8")
    errs = validate_config_file(p)
    assert any("agents_md_gate" in e.message and "mapping" in e.message for e in errs)

    p2 = tmp_path / "unk.yaml"
    p2.write_text(
        "server:\n  command: x\nagents_md_gate:\n  nope: 1\n",
        encoding="utf-8",
    )
    errs2 = validate_config_file(p2)
    assert any("Unknown key in agents_md_gate" in e.message for e in errs2)

    p3 = tmp_path / "sev.yaml"
    p3.write_text(
        "server:\n  command: x\nagents_md_gate:\n  fail_on: ultra\n",
        encoding="utf-8",
    )
    errs3 = validate_config_file(p3)
    assert any("fail_on" in e.message for e in errs3)


def test_run_scan_agents_cli_clean_and_fail(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "AGENTS.md").write_text("# clean\n", encoding="utf-8")
    assert run_scan_agents(["--dir", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "clean" in out

    (tmp_path / "AGENTS.md").write_text("x\u200by\n", encoding="utf-8")
    assert run_scan_agents(["--dir", str(tmp_path)]) == 1
    err = capsys.readouterr().err
    assert "FAIL" in err


def test_run_scan_agents_json_and_empty(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert run_scan_agents(["--dir", str(tmp_path)]) == 0
    assert "no agent rules" in capsys.readouterr().out

    (tmp_path / "AGENTS.md").write_text("z\u200b\n", encoding="utf-8")
    rc = run_scan_agents(["--dir", str(tmp_path), "--json", "--fail-on", "high"])
    assert rc == 1
    lines = [json.loads(l) for l in capsys.readouterr().out.strip().splitlines() if l]
    assert lines and lines[0]["band"] == "zero-width"


def test_cli_dispatches_scan_agents() -> None:
    from mcp_test_harness.cli import main

    with patch("mcp_test_harness.agents_md_scan.run_scan_agents", return_value=0) as m:
        assert main(["scan-agents", "--dir", "."]) == 0
        m.assert_called_once()


def test_public_exports() -> None:
    import mcp_test_harness as m

    assert callable(m.assert_agents_md_clean)
    assert callable(m.scan_project_agent_rules)
    assert m.__version__ == "5.1.0"


@pytest.mark.asyncio
async def test_scheduler_agents_md_gate_fail_fast() -> None:
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from mcp_test_harness.discovery import HarnessCase
    from mcp_test_harness.lifecycle import ManagedServer
    from mcp_test_harness.models import CaseStatus
    from mcp_test_harness.scheduler import HarnessScheduler
    from mcp_test_harness.config import HarnessConfig

    async def _pass():
        pass

    tc = HarnessCase(
        name="test_a",
        module_path=Path("test_a.py"),
        func=_pass,
        markers={},
        is_async=True,
    )
    config = HarnessConfig(
        server_command="echo",
        schema_validation=False,
        agents_md_gate=AgentsMdGatePolicy(enabled=True),
    )
    server = ManagedServer(
        process=None,
        session=MagicMock(),
        transport=MagicMock(),
        capabilities={"tools": {}},
        init_result=SimpleNamespace(protocolVersion="v1"),
    )

    with (
        patch("mcp_test_harness.scheduler.ServerLifecycleManager") as lm_cls,
        patch(
            "mcp_test_harness.scheduler.run_configured_agents_md_gate",
            side_effect=MCPAssertionError("hidden unicode"),
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
        r.name == "agents_md_gate" and r.status == CaseStatus.FAILED
        for r in run.test_results
    )
    assert any(r.status == CaseStatus.SKIPPED for r in run.test_results)
    exec_instance.execute.assert_not_called()


@pytest.mark.asyncio
async def test_scheduler_parallel_agents_md_gate_sets_fail_stop() -> None:
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from mcp_test_harness.discovery import HarnessCase
    from mcp_test_harness.lifecycle import ManagedServer
    from mcp_test_harness.models import CaseResult, CaseStatus
    from mcp_test_harness.scheduler import HarnessScheduler
    from mcp_test_harness.config import HarnessConfig

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
        agents_md_gate=AgentsMdGatePolicy(enabled=True),
    )
    server = ManagedServer(
        process=None,
        session=MagicMock(),
        transport=MagicMock(),
        capabilities={"tools": {}},
        init_result=SimpleNamespace(protocolVersion="v1"),
    )

    with (
        patch("mcp_test_harness.scheduler.ServerLifecycleManager") as lm_cls,
        patch(
            "mcp_test_harness.scheduler.run_configured_agents_md_gate",
            side_effect=MCPAssertionError("hidden"),
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

    assert any(r.name == "agents_md_gate" for r in run.test_results)
    assert any(r.status == CaseStatus.SKIPPED for r in run.test_results)
