"""Tests for audit_chain verifier and CLI."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from mcp_test_harness.assertions import MCPAssertionError
from mcp_test_harness.audit_chain import (
    GENESIS_PREV_HASH,
    assert_audit_chain_intact,
    build_audit_chain,
    compute_record_hash,
    run_audit_verify,
    verify_audit_chain,
)


def test_build_and_verify_ok() -> None:
    chain = build_audit_chain([{"event": "a"}, {"event": "b"}])
    assert chain[0]["prevHash"] == GENESIS_PREV_HASH
    assert verify_audit_chain(chain) == []
    assert_audit_chain_intact(chain)


def test_tamper_and_broken_link() -> None:
    chain = build_audit_chain([{"event": "a"}, {"event": "b"}])
    chain[1]["event"] = "mutated"
    with pytest.raises(MCPAssertionError, match="tamper"):
        assert_audit_chain_intact(chain)
    chain2 = build_audit_chain([{"event": "a"}, {"event": "b"}])
    chain2[1]["prevHash"] = "1" * 64
    assert any("broken link" in p for p in verify_audit_chain(chain2))


def test_empty_duplicate_missing_fields() -> None:
    assert "empty" in verify_audit_chain([])[0].lower()
    assert "not a mapping" in verify_audit_chain(["x"])[0]  # type: ignore[list-item]
    assert any("prevHash" in p for p in verify_audit_chain([{"hash": "ab"}]))
    assert any("missing hash" in p for p in verify_audit_chain([{"prevHash": GENESIS_PREV_HASH}]))
    chain = build_audit_chain([{"event": "a"}])
    chain.append(dict(chain[0]))
    assert any("duplicate" in p for p in verify_audit_chain(chain))


def test_compute_and_cli(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rec = {"prevHash": GENESIS_PREV_HASH, "event": "x"}
    h = compute_record_hash(rec, prev_hash=GENESIS_PREV_HASH)
    assert len(h) == 64
    chain = build_audit_chain([{"event": "ok"}])
    p = tmp_path / "chain.json"
    p.write_text(json.dumps({"records": chain}), encoding="utf-8")
    assert run_audit_verify(["verify", str(p)]) == 0
    assert "OK" in capsys.readouterr().out
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"records": []}), encoding="utf-8")
    assert run_audit_verify(["verify", str(bad)]) == 1
    assert run_audit_verify(["verify", str(tmp_path / "missing.json")]) == 2
    wrapped = tmp_path / "events.json"
    wrapped.write_text(json.dumps({"events": chain}), encoding="utf-8")
    assert run_audit_verify(["verify", str(wrapped)]) == 0
    lst = tmp_path / "list.json"
    lst.write_text(json.dumps(chain), encoding="utf-8")
    assert run_audit_verify(["verify", str(lst)]) == 0
    weird = tmp_path / "weird.json"
    weird.write_text(json.dumps({"nope": 1}), encoding="utf-8")
    assert run_audit_verify(["verify", str(weird)]) == 2


def test_cli_dispatch() -> None:
    from mcp_test_harness.cli import main

    with patch("mcp_test_harness.audit_chain.run_audit_verify", return_value=0) as m:
        assert main(["audit", "verify", "x.json"]) == 0
        m.assert_called_once()
