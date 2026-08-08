#!/usr/bin/env python3
"""Sum PyPI download counts for all harness packages into one ecosystem total.

Primary source: pepy.tech API v2 ``total_downloads`` (all-time cumulative).
Fallback: pypistats.org overall (rolling window, ~180 days) when PePy has no row yet.
New packages may 404 on both until indexed; those are recorded as pending.

Writes:
  html/assets/ecosystem-downloads.json
  html/assets/ecosystem-downloads-badge.json
  html/assets/badges/{package}-downloads.json
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "html" / "assets"
BADGES_DIR = OUT_DIR / "badges"
STATS_PATH = OUT_DIR / "ecosystem-downloads.json"
BADGE_PATH = OUT_DIR / "ecosystem-downloads-badge.json"
BADGE_RAW_BASE = (
    "https://raw.githubusercontent.com/vaquarkhan/mcp-test-harness/main/html/assets/badges"
)

# Keep in sync with README Framework Integration Packages + html/assets/package-widget.js
PACKAGES: list[tuple[str, str]] = [
    ("mcp-test-harness", "Core CLI + assertions"),
    ("mcp-test-harness-fastmcp", "FastMCP servers"),
    ("mcp-test-harness-openai", "OpenAI function calling"),
    ("mcp-test-harness-anthropic", "Anthropic Claude tool use"),
    ("mcp-test-harness-bedrock", "AWS Bedrock agents"),
    ("mcp-test-harness-gemini", "Google Gemini"),
    ("mcp-test-harness-langchain", "LangChain MCP tools"),
    ("mcp-test-harness-crewai", "CrewAI agents"),
    ("mcp-test-harness-llamaindex", "LlamaIndex tools"),
    ("mcp-test-harness-groq", "Groq inference"),
    ("mcp-test-harness-mistral", "Mistral AI"),
    ("mcp-test-harness-cohere", "Cohere"),
    ("mcp-test-harness-azure", "Azure OpenAI"),
    ("mcp-test-harness-vertexai", "Google Vertex AI"),
    ("mcp-test-harness-huggingface", "Hugging Face Inference"),
    ("mcp-test-harness-deepseek", "DeepSeek AI"),
    ("mcp-test-harness-together", "Together AI"),
    ("mcp-test-harness-fireworks", "Fireworks AI"),
    ("mcp-test-harness-ollama", "Ollama local models"),
    ("mcp-test-harness-openrouter", "OpenRouter gateway"),
    ("mcp-test-harness-litellm", "LiteLLM proxy"),
    ("mcp-test-harness-xai", "xAI Grok"),
    ("mcp-test-harness-autogen", "Microsoft AutoGen"),
]

UA = {
    "User-Agent": (
        "mcp-test-harness-ecosystem-downloads/1.0 "
        "(+https://github.com/vaquarkhan/mcp-test-harness)"
    )
}


def _fetch_pypistats_overall(name: str) -> int | None:
    """Rolling-window total from pypistats (~180 days). None if not indexed."""
    url = f"https://pypistats.org/api/packages/{name}/overall"
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = json.load(resp)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise
    rows = payload.get("data") or []
    preferred = [r for r in rows if r.get("category") == "without_mirrors"]
    if not preferred:
        preferred = [r for r in rows if r.get("category") == "with_mirrors"]
    return int(sum(int(r.get("downloads") or 0) for r in preferred))


def _fetch_pepy_total(name: str) -> int | None:
    """All-time cumulative downloads from pepy.tech. None if not indexed."""
    url = f"https://pepy.tech/api/v2/projects/{name}"
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = json.load(resp)
    except urllib.error.HTTPError as exc:
        if exc.code in {404, 401}:
            return None
        raise
    total = payload.get("total_downloads")
    return int(total) if total is not None else None


def _fetch_downloads(name: str) -> tuple[int, str, str]:
    """Return (downloads, stats_status, stats_source)."""
    pepy_total = _fetch_pepy_total(name)
    if pepy_total is not None:
        return pepy_total, "indexed", "pepy.tech all-time"

    pypistats_total = _fetch_pypistats_overall(name)
    if pypistats_total is not None:
        return pypistats_total, "indexed", "pypistats.org (~180d window)"

    return 0, "pending", "none"


def _format_count(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M".replace(".0M", "M")
    if n >= 1_000:
        return f"{n / 1_000:.1f}k".replace(".0k", "k")
    return str(n)


def _write_package_badge(name: str, downloads: int, stats_status: str) -> str:
    """Write Shields endpoint JSON for one package; return its raw GitHub URL."""
    BADGES_DIR.mkdir(parents=True, exist_ok=True)
    path = BADGES_DIR / f"{name}-downloads.json"
    label = "total downloads" if stats_status == "indexed" else "downloads"
    if stats_status == "indexed" and downloads > 0:
        message = _format_count(downloads)
        color = "0B5FFF"
    elif stats_status == "indexed":
        message = "0"
        color = "lightgrey"
    else:
        message = "on PyPI"
        color = "lightgrey"
    path.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "label": label,
                "message": message,
                "color": color,
                "cacheSeconds": 3600,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return f"{BADGE_RAW_BASE}/{name}-downloads.json"


def _shields_endpoint(raw_badge_url: str) -> str:
    return f"https://img.shields.io/endpoint?url={quote(raw_badge_url, safe='')}"


def main() -> None:
    per_package: list[dict] = []
    total = 0
    pending_count = 0
    for i, (name, protects) in enumerate(PACKAGES):
        if i:
            time.sleep(0.35)
        downloads, stats_status, stats_source = _fetch_downloads(name)
        total += downloads
        if stats_status == "pending":
            pending_count += 1
        badge_raw = _write_package_badge(name, downloads, stats_status)
        per_package.append(
            {
                "package": name,
                "protects": protects,
                "downloads": downloads,
                "stats_status": stats_status,
                "stats_source": stats_source,
                "badge_raw": badge_raw,
                "badge_shields": _shields_endpoint(badge_raw),
                "pypi": f"https://pypi.org/project/{name}/",
                "pepy": f"https://pepy.tech/projects/{name}",
                "pypistats": f"https://pypistats.org/packages/{name}",
            }
        )
        print(f"{name}: {downloads} ({stats_status}, {stats_source})")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    stats = {
        "updated_at": now,
        "source": "pepy.tech total_downloads (all-time); pypistats.org fallback (~180d)",
        "note": (
            "All-time cumulative per package when PePy has indexed the project. "
            "New releases show stats_status=pending until PePy/pypistats index them "
            "(usually 24–48h). Installing an integration also pulls mcp-test-harness, "
            "so core + integration totals can overlap."
        ),
        "package_count": len(PACKAGES),
        "indexed_count": len(PACKAGES) - pending_count,
        "pending_count": pending_count,
        "total_downloads": total,
        "packages": per_package,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    STATS_PATH.write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    BADGE_PATH.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "label": "ecosystem total",
                "message": _format_count(total),
                "color": "0B5FFF",
                "namedLogo": "python",
                "cacheSeconds": 3600,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"total_downloads={total} -> {STATS_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
