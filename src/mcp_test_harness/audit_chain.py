"""Deterministic SHA-256 audit-chain verifier (Bastion Extension F pairing).

Proves records were not altered, truncated, or reordered undetected.
Does **not** prove that no records were omitted without an external anchor.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

from mcp_test_harness.assertions import MCPAssertionError

GENESIS_PREV_HASH = "0" * 64


def _canonical_payload(record: Mapping[str, Any]) -> bytes:
    """Canonical JSON bytes of the record excluding the hash field itself."""
    body = {k: v for k, v in record.items() if k not in ("hash", "recordHash", "digest")}
    return json.dumps(body, sort_keys=True, separators=(",", ":"), default=str).encode(
        "utf-8"
    )


def compute_record_hash(record: Mapping[str, Any], *, prev_hash: str) -> str:
    """Compute SHA-256 hex digest for *record* chained from *prev_hash*."""
    material = prev_hash.encode("ascii") + _canonical_payload(record)
    return hashlib.sha256(material).hexdigest()


def _record_hash_field(record: Mapping[str, Any]) -> str | None:
    for key in ("hash", "recordHash", "digest"):
        if key in record and record[key] is not None:
            return str(record[key])
    return None


def _prev_hash_field(record: Mapping[str, Any]) -> str | None:
    for key in ("prevHash", "previousHash", "prev_hash"):
        if key in record and record[key] is not None:
            return str(record[key])
    return None


def verify_audit_chain(
    records: Sequence[Mapping[str, Any]],
    *,
    genesis_prev_hash: str = GENESIS_PREV_HASH,
) -> list[str]:
    """Return human-readable problems; empty list means intact."""
    if not records:
        return ["audit chain is empty (truncation or missing genesis)"]
    problems: list[str] = []
    expected_prev = genesis_prev_hash
    seen_hashes: set[str] = set()
    for idx, rec in enumerate(records):
        if not isinstance(rec, Mapping):
            problems.append(f"record[{idx}] is not a mapping")
            continue
        prev = _prev_hash_field(rec)
        got = _record_hash_field(rec)
        if prev is None:
            problems.append(f"record[{idx}] missing prevHash")
            continue
        if got is None:
            problems.append(f"record[{idx}] missing hash")
            continue
        if prev != expected_prev:
            problems.append(
                f"record[{idx}] broken link: prevHash={prev!r} expected={expected_prev!r}"
            )
        expected = compute_record_hash(rec, prev_hash=prev)
        if got != expected:
            problems.append(
                f"record[{idx}] tamper: hash={got!r} recomputed={expected!r}"
            )
        if got in seen_hashes:
            problems.append(f"record[{idx}] duplicate hash (reorder/replay): {got}")
        seen_hashes.add(got)
        expected_prev = got
    return problems


def assert_audit_chain_intact(
    records: Sequence[Mapping[str, Any]],
    *,
    genesis_prev_hash: str = GENESIS_PREV_HASH,
) -> None:
    """Fail when the audit chain is broken, tampered, truncated, or reordered."""
    problems = verify_audit_chain(records, genesis_prev_hash=genesis_prev_hash)
    if problems:
        raise MCPAssertionError(
            "Audit chain integrity failed:\n" + "\n".join(f"  - {p}" for p in problems)
        )


def build_audit_chain(
    payloads: Sequence[Mapping[str, Any]],
    *,
    genesis_prev_hash: str = GENESIS_PREV_HASH,
) -> list[dict[str, Any]]:
    """Helper for fixtures/tests: stamp prevHash/hash onto payload dicts."""
    out: list[dict[str, Any]] = []
    prev = genesis_prev_hash
    for payload in payloads:
        rec = dict(payload)
        rec["prevHash"] = prev
        rec["hash"] = compute_record_hash(rec, prev_hash=prev)
        out.append(rec)
        prev = rec["hash"]
    return out


def _load_records(path: Path) -> list[Mapping[str, Any]]:
    text = path.read_text(encoding="utf-8")
    data = json.loads(text)
    if isinstance(data, list):
        return list(data)
    if isinstance(data, dict):
        for key in ("records", "events", "chain"):
            if isinstance(data.get(key), list):
                return list(data[key])
    raise ValueError(f"Unsupported audit file shape in {path}")


def run_audit_verify(argv: list[str] | None = None) -> int:
    """CLI: ``mcp-test audit verify <file>``."""
    parser = argparse.ArgumentParser(
        prog="mcp-test audit",
        description="Verify a Bastion-style SHA-256 audit chain file (JSON).",
    )
    sub = parser.add_subparsers(dest="action", required=True)
    verify = sub.add_parser("verify", help="Recompute chain and exit 1 on failure")
    verify.add_argument("file", type=Path, help="JSON file with records[] or a list")
    args = parser.parse_args(argv)
    try:
        records = _load_records(args.file)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"audit verify: {exc}", file=sys.stderr)
        return 2
    problems = verify_audit_chain(records)
    if problems:
        print("audit verify FAILED:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1
    print(f"audit verify OK ({len(records)} record(s))")
    return 0
