"""Deterministic MCP manifest / rug-pull gate.

Captures the sanctioned server surface (capabilities, tools, resources,
prompts — names, descriptions, schemas) and fails CI when it changes
without an explicit snapshot update. Scanners see *current* state; this
gate enforces a *baseline* at merge time.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mcp_test_harness.assertions import MCPAssertionError
from mcp_test_harness.snapshots import SnapshotManager, cli_update_snapshots


@dataclass(frozen=True)
class ManifestGatePolicy:
    """Opt-in ``manifest_gate:`` config (disabled by default — non-breaking)."""

    enabled: bool = False
    path: str = "__snapshots__/mcp_manifest.snap"


def parse_manifest_gate_policy(raw: dict[str, Any] | None) -> ManifestGatePolicy:
    data = raw or {}
    path = data.get("path", "__snapshots__/mcp_manifest.snap")
    return ManifestGatePolicy(
        enabled=bool(data.get("enabled", False)),
        path=str(path),
    )


def _item_list(result: Any, singular: str) -> list[Any]:
    if isinstance(result, dict):
        raw = result.get(singular, result.get(singular + "s", []))
    else:
        raw = getattr(result, singular, None) or getattr(result, singular + "s", None)
    if raw is None:
        raw = result if isinstance(result, list) else []
    return list(raw) if isinstance(raw, list) else []


def _to_plain(obj: Any) -> Any:
    """Best-effort JSON-serialisable form of MCP SDK objects / dicts."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {str(k): _to_plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_plain(v) for v in obj]
    model_dump = getattr(obj, "model_dump", None)
    if callable(model_dump):
        try:
            try:
                dumped = model_dump(mode="json", by_alias=True)
            except TypeError:
                dumped = model_dump()
            return _to_plain(dumped)
        except Exception:
            pass
    if hasattr(obj, "__dict__"):
        data = {
            k: v
            for k, v in vars(obj).items()
            if not k.startswith("_") and not callable(v)
        }
        if data:
            return _to_plain(data)
    return str(obj)


def _normalize_tool(tool: Any) -> dict[str, Any]:
    plain = _to_plain(tool)
    if not isinstance(plain, dict):
        return {"raw": plain}
    name = plain.get("name", "")
    return {
        "name": name,
        "description": plain.get("description") or "",
        "inputSchema": plain.get("inputSchema")
        or plain.get("input_schema")
        or {"type": "object", "properties": {}},
        "annotations": plain.get("annotations"),
    }


def _normalize_resource(resource: Any) -> dict[str, Any]:
    plain = _to_plain(resource)
    if not isinstance(plain, dict):
        return {"raw": plain}
    return {
        "uri": str(plain.get("uri", "")),
        "name": plain.get("name") or "",
        "description": plain.get("description") or "",
        "mimeType": plain.get("mimeType") or plain.get("mime_type"),
    }


def _normalize_prompt(prompt: Any) -> dict[str, Any]:
    plain = _to_plain(prompt)
    if not isinstance(plain, dict):
        return {"raw": plain}
    return {
        "name": plain.get("name") or "",
        "description": plain.get("description") or "",
        "arguments": plain.get("arguments") or [],
    }


def normalize_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    """Stable, sorted form for deterministic comparison."""
    tools = sorted(
        (_normalize_tool(t) for t in manifest.get("tools") or []),
        key=lambda t: str(t.get("name", "")),
    )
    resources = sorted(
        (_normalize_resource(r) for r in manifest.get("resources") or []),
        key=lambda r: str(r.get("uri", "")),
    )
    prompts = sorted(
        (_normalize_prompt(p) for p in manifest.get("prompts") or []),
        key=lambda p: str(p.get("name", "")),
    )
    caps = _to_plain(manifest.get("capabilities") or {})
    return {
        "protocolVersion": manifest.get("protocolVersion") or "",
        "capabilities": caps if isinstance(caps, dict) else {"value": caps},
        "tools": tools,
        "resources": resources,
        "prompts": prompts,
    }


async def capture_server_manifest(
    session: Any,
    *,
    capabilities: dict[str, Any] | None = None,
    protocol_version: str | None = None,
) -> dict[str, Any]:
    """Build a full MCP surface manifest from a live session."""
    tools: list[Any] = []
    resources: list[Any] = []
    prompts: list[Any] = []
    try:
        tools = _item_list(await session.list_tools(), "tool")
    except Exception:
        tools = []
    try:
        resources = _item_list(await session.list_resources(), "resource")
    except Exception:
        resources = []
    try:
        prompts = _item_list(await session.list_prompts(), "prompt")
    except Exception:
        prompts = []

    proto = protocol_version or ""
    if not proto:
        init = getattr(session, "initialize_result", None) or getattr(
            session, "init_result", None
        )
        if init is not None:
            proto = str(
                getattr(init, "protocolVersion", None)
                or (init.get("protocolVersion") if isinstance(init, dict) else "")
                or ""
            )

    caps = capabilities
    if caps is None:
        caps = getattr(session, "capabilities", None) or {}

    return normalize_manifest(
        {
            "protocolVersion": proto,
            "capabilities": caps,
            "tools": tools,
            "resources": resources,
            "prompts": prompts,
        }
    )


def _diff_summary(stored: dict[str, Any], actual: dict[str, Any]) -> str:
    """Human-readable rug-pull summary (plus JSON unified-style hint)."""
    lines: list[str] = []
    for section, key in (
        ("tools", "name"),
        ("resources", "uri"),
        ("prompts", "name"),
    ):
        old = {str(i.get(key)): i for i in stored.get(section) or [] if isinstance(i, dict)}
        new = {str(i.get(key)): i for i in actual.get(section) or [] if isinstance(i, dict)}
        added = sorted(set(new) - set(old))
        removed = sorted(set(old) - set(new))
        changed = sorted(
            k for k in set(old) & set(new) if old[k] != new[k]
        )
        if added:
            lines.append(f"{section} added: {', '.join(added)}")
        if removed:
            lines.append(f"{section} removed: {', '.join(removed)}")
        if changed:
            lines.append(f"{section} changed: {', '.join(changed)}")
    if stored.get("capabilities") != actual.get("capabilities"):
        lines.append("capabilities changed")
    if stored.get("protocolVersion") != actual.get("protocolVersion"):
        lines.append(
            f"protocolVersion changed: {stored.get('protocolVersion')!r} → "
            f"{actual.get('protocolVersion')!r}"
        )
    if not lines:
        lines.append("manifest JSON differs (see snapshot diff)")
    return "; ".join(lines)


async def assert_manifest_snapshot(
    session: Any,
    path: str | Path,
    *,
    update: bool = False,
    capabilities: dict[str, Any] | None = None,
    protocol_version: str | None = None,
) -> dict[str, Any]:
    """Compare the live MCP manifest to a sanctioned baseline file.

    * Creates the baseline when missing (first run).
    * With ``update=True`` or ``--update-snapshots``, rewrites the baseline.
    * On mismatch raises :class:`MCPAssertionError` with a rug-pull summary.
    """
    actual = await capture_server_manifest(
        session,
        capabilities=capabilities,
        protocol_version=protocol_version,
    )
    snap_path = Path(path)
    effective_update = update or cli_update_snapshots()
    mgr = SnapshotManager(update=effective_update)
    stored = mgr.read_snapshot(snap_path)

    if stored is None or effective_update:
        mgr.write_snapshot(snap_path, actual)
        return actual

    stored_n = normalize_manifest(stored if isinstance(stored, dict) else {})
    if json.dumps(stored_n, sort_keys=True, default=str) != json.dumps(
        actual, sort_keys=True, default=str
    ):
        summary = _diff_summary(stored_n, actual)
        diff = mgr.diff(stored_n, actual)
        raise MCPAssertionError(
            f"MCP manifest rug-pull detected ({summary}).\n"
            f"Approve intentional surface changes with "
            f"`mcp-test --update-snapshots` or `mcp-test manifest update`.\n"
            f"{diff}"
        )
    return actual


def evaluate_manifest_gate_error(exc: BaseException) -> str:
    """Format a gate failure message for CaseResult / quality_gate reasons."""
    return str(exc)


async def run_configured_manifest_gate(
    session: Any,
    policy: ManifestGatePolicy | None,
    *,
    capabilities: dict[str, Any] | None = None,
    protocol_version: str | None = None,
) -> dict[str, Any] | None:
    """Run the config-driven gate. Returns ``None`` if disabled or matching.

    Raises :class:`MCPAssertionError` on rug-pull (caller turns into CaseResult).
    """
    if policy is None or not policy.enabled:
        return None
    return await assert_manifest_snapshot(
        session,
        policy.path,
        update=False,
        capabilities=capabilities,
        protocol_version=protocol_version,
    )


# ---------------------------------------------------------------------------
# CLI: mcp-test manifest {check|update|show}
# ---------------------------------------------------------------------------


def _build_manifest_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="mcp-test manifest",
        description="Capture or gate the MCP server surface (rug-pull / supply-chain).",
    )
    p.add_argument(
        "action",
        choices=["check", "update", "show"],
        help="check=compare to baseline; update=rewrite baseline; show=print JSON",
    )
    p.add_argument("--dir", dest="root", default=".", help="Project root (default: .)")
    p.add_argument(
        "--path",
        default="__snapshots__/mcp_manifest.snap",
        help="Baseline path (default: __snapshots__/mcp_manifest.snap)",
    )
    p.add_argument("--config", default=None, help="Path to mcp-test.yaml / toml")
    p.add_argument("--server-command", default=None)
    p.add_argument("--transport", default=None, choices=["stdio", "sse", "http"])
    return p


async def run_manifest_async(argv: list[str] | None) -> int:
    from argparse import Namespace

    from mcp_test_harness.config import load_config
    from mcp_test_harness.lifecycle import ServerLifecycleManager, StartupError

    parser = _build_manifest_parser()
    args = parser.parse_args(argv)
    ns = Namespace(
        test_path="tests",
        version=False,
        list=False,
        watch=False,
        config=args.config,
        server_command=args.server_command,
        transport=args.transport,
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
    try:
        config = load_config(ns)
    except SystemExit:
        return 2

    root = Path(args.root).resolve()
    snap_path = Path(args.path)
    if not snap_path.is_absolute():
        snap_path = root / snap_path

    lifecycle = ServerLifecycleManager()
    server = None
    try:
        server = await lifecycle.start(config)
        caps = dict(server.capabilities or {})
        proto = (
            ServerLifecycleManager.protocol_version_from_init(server.init_result) or ""
        )
        if args.action == "show":
            manifest = await capture_server_manifest(
                server.session, capabilities=caps, protocol_version=proto
            )
            print(json.dumps(manifest, indent=2, sort_keys=True))
            return 0
        if args.action == "update":
            await assert_manifest_snapshot(
                server.session,
                snap_path,
                update=True,
                capabilities=caps,
                protocol_version=proto,
            )
            print(f"Wrote manifest baseline {snap_path}")
            return 0
        # check
        try:
            await assert_manifest_snapshot(
                server.session,
                snap_path,
                update=False,
                capabilities=caps,
                protocol_version=proto,
            )
        except MCPAssertionError as exc:
            print(f"manifest check failed: {exc}", file=sys.stderr)
            return 1
        print(f"Manifest matches baseline {snap_path}")
        return 0
    except StartupError as exc:
        print(f"manifest: server failed to start: {exc}", file=sys.stderr)
        return 1
    finally:
        if server is not None:
            await lifecycle.shutdown(server)


def run_manifest(argv: list[str] | None = None) -> int:
    return asyncio.run(run_manifest_async(argv))
