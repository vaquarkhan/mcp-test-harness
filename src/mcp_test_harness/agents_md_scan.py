"""Defensive scan for hidden Unicode in agent instruction files.

Research (CSA / Knostic / Trojan Source class): ``AGENTS.md``, ``CLAUDE.md``,
``.cursorrules``, and skill files can carry invisible Unicode Tags-block
smuggling, zero-width steganography, or bidi overrides that humans do not see
but models still tokenize.

This module is a **CI gate only** — it detects and reports known invisible
codepoints. It does not generate attack payloads or run live red-team agents.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

from mcp_test_harness.assertions import MCPAssertionError

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_AGENT_RULE_NAMES: tuple[str, ...] = (
    "AGENTS.md",
    "AGENT.md",
    "CLAUDE.md",
    ".cursorrules",
    ".clinerules",
)

# Severity ranks for fail_on thresholds (higher = more severe).
_SEVERITY_RANK: dict[str, int] = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}

# Named bands of invisible / deceptive codepoints (defensive catalogue).
_BANDS: tuple[tuple[str, str, str, frozenset[int] | range], ...] = (
    (
        "unicode-tags",
        "critical",
        "Unicode Tags block (invisible ASCII smuggling)",
        range(0xE0000, 0xE007F + 1),
    ),
    (
        "bidi-override",
        "critical",
        "Bidirectional override (Trojan Source)",
        frozenset(range(0x202A, 0x202E + 1)),
    ),
    (
        "bidi-isolate",
        "high",
        "Bidirectional isolate",
        frozenset(range(0x2066, 0x2069 + 1)),
    ),
    (
        "zero-width",
        "high",
        "Zero-width / word-joiner invisible character",
        frozenset(
            {
                0x200B,  # ZWSP
                0x200C,  # ZWNJ
                0x200D,  # ZWJ
                0x2060,  # word joiner
                0x2061,
                0x2062,
                0x2063,
                0x2064,
                0x00AD,  # soft hyphen
            }
        ),
    ),
    (
        "bom",
        "medium",
        "Byte order mark (suspicious when not at file start)",
        frozenset({0xFEFF}),
    ),
)


@dataclass(frozen=True)
class HiddenUnicodeFinding:
    """One suspicious codepoint occurrence in an agent rules file."""

    path: str
    line: int
    column: int
    codepoint: str
    band: str
    severity: str
    detail: str
    decoded_hint: str = ""


@dataclass(frozen=True)
class AgentsMdGatePolicy:
    """Opt-in ``agents_md_gate:`` config (disabled by default — non-breaking)."""

    enabled: bool = False
    paths: tuple[str, ...] = ()
    fail_on: str = "high"
    strict: bool = False
    root: str = "."


def parse_agents_md_gate_policy(raw: dict[str, Any] | None) -> AgentsMdGatePolicy:
    """Parse ``agents_md_gate:`` mapping; empty/None → disabled policy."""
    if not raw:
        return AgentsMdGatePolicy()
    fail_on = str(raw.get("fail_on", "high")).lower()
    if fail_on not in _SEVERITY_RANK:
        raise ValueError(
            "agents_md_gate.fail_on must be one of "
            + ", ".join(sorted(_SEVERITY_RANK))
        )
    paths_raw = raw.get("paths") or ()
    if isinstance(paths_raw, str):
        paths: tuple[str, ...] = (paths_raw,)
    else:
        paths = tuple(str(p) for p in paths_raw)
    return AgentsMdGatePolicy(
        enabled=bool(raw.get("enabled", False)),
        paths=paths,
        fail_on=fail_on,
        strict=bool(raw.get("strict", False)),
        root=str(raw.get("root", ".")),
    )


def _classify(cp: int) -> tuple[str, str, str] | None:
    for band, severity, detail, members in _BANDS:
        if isinstance(members, range):
            if cp in members:
                return band, severity, detail
        elif cp in members:
            return band, severity, detail
    return None


def _decode_tags_hint(text: str) -> str:
    """Best-effort decode of Tags-block smuggled ASCII for CI reviewers."""
    chars: list[str] = []
    for ch in text:
        cp = ord(ch)
        if 0xE0020 <= cp <= 0xE007E:
            chars.append(chr(cp - 0xE0000))
        elif cp == 0xE0001 or cp == 0xE007F:
            continue
    return "".join(chars)


def scan_text_for_hidden_unicode(
    text: str,
    *,
    path: str = "<string>",
    strict: bool = False,
) -> list[HiddenUnicodeFinding]:
    """Scan *text* for known invisible / deceptive Unicode bands."""
    findings: list[HiddenUnicodeFinding] = []
    line = 1
    col = 1
    for idx, ch in enumerate(text):
        cp = ord(ch)
        if ch == "\n":
            line += 1
            col = 1
            continue
        classified = _classify(cp)
        if classified is None:
            col += 1
            continue
        band, severity, detail = classified
        if band == "bom" and idx == 0:
            # Leading BOM is common in UTF-8 files — only flag mid-file / strict.
            if not strict:
                col += 1
                continue
            detail = "Leading BOM (strict mode)"
            severity = "low"
        decoded = ""
        if band == "unicode-tags":
            # Peek local window for a readable smuggled fragment.
            window = text[max(0, idx - 8) : idx + 48]
            decoded = _decode_tags_hint(window)
        findings.append(
            HiddenUnicodeFinding(
                path=path,
                line=line,
                column=col,
                codepoint=f"U+{cp:04X}",
                band=band,
                severity=severity,
                detail=detail,
                decoded_hint=decoded,
            )
        )
        col += 1
    return findings


def resolve_agent_rule_paths(
    root: str | Path,
    paths: Sequence[str] | None = None,
) -> list[Path]:
    """Resolve existing agent-rule files under *root*."""
    base = Path(root).resolve()
    if paths:
        out: list[Path] = []
        for p in paths:
            cand = Path(p)
            if not cand.is_absolute():
                cand = base / cand
            if cand.is_file():
                out.append(cand.resolve())
        return out
    found: list[Path] = []
    for name in DEFAULT_AGENT_RULE_NAMES:
        cand = base / name
        if cand.is_file():
            found.append(cand.resolve())
    # Optional Cursor rules / skills when present (still defensive, read-only).
    cursor_rules = base / ".cursor" / "rules"
    if cursor_rules.is_dir():
        found.extend(sorted(p.resolve() for p in cursor_rules.glob("*.mdc") if p.is_file()))
        found.extend(sorted(p.resolve() for p in cursor_rules.glob("*.md") if p.is_file()))
    skills = base / "skills"
    if skills.is_dir():
        found.extend(sorted(p.resolve() for p in skills.rglob("SKILL.md") if p.is_file()))
    # Deduplicate while preserving order
    seen: set[Path] = set()
    unique: list[Path] = []
    for p in found:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    return unique


def scan_agents_md_paths(
    paths: Iterable[str | Path],
    *,
    strict: bool = False,
) -> list[HiddenUnicodeFinding]:
    """Scan each existing file path; skip missing paths silently."""
    all_findings: list[HiddenUnicodeFinding] = []
    for raw in paths:
        path = Path(raw)
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="surrogatepass")
        try:
            rel = str(path)
        except Exception:  # pragma: no cover
            rel = path.name
        all_findings.extend(
            scan_text_for_hidden_unicode(text, path=rel, strict=strict)
        )
    return all_findings


def scan_project_agent_rules(
    root: str | Path = ".",
    *,
    paths: Sequence[str] | None = None,
    strict: bool = False,
) -> list[HiddenUnicodeFinding]:
    """Discover and scan agent instruction files under *root*."""
    return scan_agents_md_paths(
        resolve_agent_rule_paths(root, paths),
        strict=strict,
    )


def _meets_threshold(severity: str, fail_on: str) -> bool:
    return _SEVERITY_RANK.get(severity, 0) >= _SEVERITY_RANK.get(fail_on, 3)


def filter_findings(
    findings: Sequence[HiddenUnicodeFinding],
    *,
    fail_on: str = "high",
) -> list[HiddenUnicodeFinding]:
    """Keep findings at or above *fail_on* severity."""
    return [f for f in findings if _meets_threshold(f.severity, fail_on)]


def format_findings(findings: Sequence[HiddenUnicodeFinding]) -> str:
    """Human-readable multi-line report for CLI / assertion errors."""
    lines: list[str] = []
    for f in findings:
        hint = f" decoded={f.decoded_hint!r}" if f.decoded_hint else ""
        lines.append(
            f"{f.path}:{f.line}:{f.column}: [{f.severity}] {f.band} "
            f"{f.codepoint} — {f.detail}{hint}"
        )
    return "\n".join(lines)


def assert_agents_md_clean(
    path: str | Path | Sequence[str | Path] | None = None,
    *,
    root: str | Path = ".",
    fail_on: str = "high",
    strict: bool = False,
) -> list[HiddenUnicodeFinding]:
    """Fail when agent rules files contain hidden Unicode at/above *fail_on*.

    *path* may be a single file, a list of files, or ``None`` to auto-discover
    under *root* (``AGENTS.md``, ``CLAUDE.md``, ``.cursorrules``, …).
    """
    if path is None:
        findings = scan_project_agent_rules(root, strict=strict)
    elif isinstance(path, (str, Path)):
        findings = scan_agents_md_paths([path], strict=strict)
    else:
        findings = scan_agents_md_paths(path, strict=strict)
    bad = filter_findings(findings, fail_on=fail_on)
    if bad:
        raise MCPAssertionError(
            f"Agent rules file(s) contain {len(bad)} hidden Unicode finding(s) "
            f"(fail_on={fail_on}):\n"
            + format_findings(bad[:32])
            + (
                f"\n  … and {len(bad) - 32} more"
                if len(bad) > 32
                else ""
            )
        )
    return list(findings)


def run_configured_agents_md_gate(
    policy: AgentsMdGatePolicy | None,
    *,
    root: str | Path | None = None,
) -> list[HiddenUnicodeFinding] | None:
    """Run the config-driven gate. Returns ``None`` if disabled.

    Raises :class:`MCPAssertionError` when findings meet the fail threshold.
    """
    if policy is None or not policy.enabled:
        return None
    base = Path(root) if root is not None else Path(policy.root)
    findings = scan_project_agent_rules(
        base,
        paths=policy.paths or None,
        strict=policy.strict,
    )
    bad = filter_findings(findings, fail_on=policy.fail_on)
    if bad:
        raise MCPAssertionError(
            f"agents_md_gate failed: {len(bad)} finding(s) "
            f"(fail_on={policy.fail_on}):\n"
            + format_findings(bad[:32])
        )
    return findings


# ---------------------------------------------------------------------------
# CLI: mcp-test scan-agents
# ---------------------------------------------------------------------------


def _build_scan_agents_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="mcp-test scan-agents",
        description=(
            "Scan AGENTS.md / CLAUDE.md / .cursorrules (and optional Cursor "
            "rules / skills) for hidden Unicode used in instruction smuggling."
        ),
    )
    p.add_argument(
        "--dir",
        dest="root",
        default=".",
        help="Project root to search (default: .)",
    )
    p.add_argument(
        "--path",
        action="append",
        dest="paths",
        default=None,
        help="Explicit file to scan (repeatable). Default: discover common names.",
    )
    p.add_argument(
        "--fail-on",
        default="high",
        choices=sorted(_SEVERITY_RANK),
        help="Minimum severity that fails the scan (default: high)",
    )
    p.add_argument(
        "--strict",
        action="store_true",
        help="Also flag leading BOM as low severity",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Emit findings as JSON lines on stdout",
    )
    return p


def run_scan_agents(argv: list[str] | None = None) -> int:
    """Sync CLI entry for ``mcp-test scan-agents``."""
    import json

    parser = _build_scan_agents_parser()
    args = parser.parse_args(argv)
    findings = scan_project_agent_rules(
        args.root,
        paths=args.paths,
        strict=args.strict,
    )
    bad = filter_findings(findings, fail_on=args.fail_on)
    if args.json:
        for f in findings:
            print(
                json.dumps(
                    {
                        "path": f.path,
                        "line": f.line,
                        "column": f.column,
                        "codepoint": f.codepoint,
                        "band": f.band,
                        "severity": f.severity,
                        "detail": f.detail,
                        "decoded_hint": f.decoded_hint,
                    },
                    sort_keys=True,
                )
            )
    else:
        scanned = resolve_agent_rule_paths(args.root, args.paths)
        if not scanned:
            print(
                "scan-agents: no agent rules files found "
                f"(looked under {Path(args.root).resolve()})",
            )
        elif not findings:
            print(f"scan-agents: clean ({len(scanned)} file(s) scanned)")
        else:
            print(format_findings(findings), file=sys.stderr if bad else sys.stdout)
    if bad:
        if not args.json:
            print(
                f"scan-agents: FAIL — {len(bad)} finding(s) at/above {args.fail_on}",
                file=sys.stderr,
            )
        return 1
    return 0
