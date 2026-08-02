"""HTML report generator for the MCP Test Harness.

Generates a self-contained HTML page with inline CSS and a small amount of
client-side script for filtering and sorting. No network requests.
"""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime
from html import escape as _html_escape
from pathlib import Path

from mcp_test_harness.models import CaseResult, CaseStatus, SessionResults
from mcp_test_harness.reporting import (
    ConsoleReporter,
    JSONReporter,
    JUnitXMLReporter,
    _suite_duration_percentiles,
)
from mcp_test_harness.security_rules import build_security_findings

# Public product URLs (linked from reports; HTML remains usable offline).
PRODUCT_SITE = "https://vaquarkhan.github.io/mcp-test-harness/"
GITHUB_REPO = "https://github.com/vaquarkhan/mcp-test-harness"
PYPI_URL = "https://pypi.org/project/mcp-test-harness/"


def _status_label(status: CaseStatus) -> str:
    return {
        CaseStatus.PASSED: "PASS",
        CaseStatus.FAILED: "FAIL",
        CaseStatus.ERROR: "ERROR",
        CaseStatus.TIMEOUT: "TIMEOUT",
        CaseStatus.SKIPPED: "SKIP",
    }.get(status, "?")


def _status_class(status: CaseStatus) -> str:
    return {
        CaseStatus.PASSED: "pass",
        CaseStatus.FAILED: "fail",
        CaseStatus.ERROR: "error",
        CaseStatus.TIMEOUT: "timeout",
        CaseStatus.SKIPPED: "skip",
    }.get(status, "")


def _outcome_tally(results: SessionResults) -> tuple[int, int, int, int, int]:
    return (
        results.passed,
        results.failed,
        results.errored,
        results.skipped,
        results.timed_out,
    )


def _quality_ok(results: SessionResults) -> bool:
    p, f, e, _sk, t = _outcome_tally(results)
    return f + e + t == 0


def _conic_gradient_pie_style(results: SessionResults) -> str:
    p, f, e, sk, t = _outcome_tally(results)
    spec = [
        (p, "#1abc7a"),
        (f, "#e74c3c"),
        (e, "#f39c12"),
        (sk, "#7f8c8d"),
        (t, "#9b59b6"),
    ]
    tot = p + f + e + sk + t
    if tot == 0:
        return "conic-gradient(#2d3748 0turn 1turn)"
    parts: list[str] = []
    a = 0.0
    for n, col in spec:
        if n == 0:
            continue
        da = 360.0 * n / tot
        b = a + da
        parts.append(f"{col} {a:.3f}deg {b:.3f}deg")
        a = b
    return "conic-gradient(" + ", ".join(parts) + ")"


def _display_file(tr: CaseResult) -> str:
    return (tr.file or tr.module).replace("\\", "/")


def _search_blob(tr: CaseResult) -> str:
    parts = [
        tr.name,
        _display_file(tr),
        tr.status.value,
        " ".join(tr.tags),
        "flaky" if tr.flaky else "",
    ]
    return " ".join(parts).lower()


def _format_duration_ms(ms: float) -> str:
    if ms >= 1000:
        return f"{ms / 1000:.2f}s"
    return f"{ms:.1f}ms"


def _iso_epoch_ms(iso: str | None) -> int | None:
    """Parse ISO-8601 timestamp to epoch milliseconds for client-side filters."""
    if not iso:
        return None
    try:
        normalized = iso.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        return int(dt.timestamp() * 1000)
    except (ValueError, OSError, OverflowError):
        return None


def _format_started_at(iso: str | None) -> str:
    """Compact UTC label for the Started column."""
    if not iso:
        return "—"
    try:
        normalized = iso.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except (ValueError, OSError, OverflowError):
        return iso[:19] if iso else "—"


def _run_epoch_bounds(results: SessionResults) -> tuple[int | None, int | None]:
    """Session start/end in epoch ms for date-range filter defaults."""
    start_ms = _iso_epoch_ms(results.started_at or None)
    end_ms = _iso_epoch_ms(results.finished_at or None)
    if end_ms is None and start_ms is not None:
        end_ms = start_ms + int(results.total_duration_ms)
    if start_ms is None:
        for tr in results.test_results:
            ms = _iso_epoch_ms(tr.started_at)
            if ms is not None:
                start_ms = ms if start_ms is None else min(start_ms, ms)
    if end_ms is None:
        for tr in results.test_results:
            ms = _iso_epoch_ms(tr.started_at)
            if ms is not None:
                end_ms = ms + int(tr.duration_ms)
    return start_ms, end_ms


def _product_logo_svg() -> str:
    """Inline SVG brand mark (no network, no binary embed)."""
    return (
        '<svg class="brand-logo" xmlns="http://www.w3.org/2000/svg" width="36" height="36" '
        'viewBox="0 0 36 36" aria-hidden="true" focusable="false">'
        '<defs><linearGradient id="mth-grad" x1="0%" y1="0%" x2="100%" y2="100%">'
        '<stop offset="0%" stop-color="#6366f1"/><stop offset="100%" stop-color="#10b981"/>'
        '</linearGradient></defs>'
        '<rect width="36" height="36" rx="9" fill="url(#mth-grad)"/>'
        '<text x="18" y="23" text-anchor="middle" fill="#fff" font-family="Segoe UI,system-ui,sans-serif" '
        'font-size="13" font-weight="800">MT</text></svg>'
    )


def _product_brand_bar_html(harness_version: str) -> str:
    """Top bar: product logo, site links, and PDF export (JMeter-style print summary)."""
    h_ver = _html_escape(harness_version or "")
    site = _html_escape(PRODUCT_SITE)
    gh = _html_escape(GITHUB_REPO)
    pypi = _html_escape(PYPI_URL)
    return (
        f'<div class="product-brand">'
        f'<a class="brand-link" href="{site}" target="_blank" rel="noopener noreferrer" '
        f'title="MCP Test Harness product site">'
        f'{_product_logo_svg()}'
        f'<span class="brand-text">MCP Test Harness</span>'
        f'<span class="brand-ver">v{h_ver}</span></a>'
        f'<nav class="brand-nav no-print" aria-label="Product links">'
        f'<a href="{site}" target="_blank" rel="noopener noreferrer">Product site</a>'
        f'<a href="{gh}" target="_blank" rel="noopener noreferrer">GitHub</a>'
        f'<a href="{pypi}" target="_blank" rel="noopener noreferrer">PyPI</a>'
        f'</nav>'
        f'<div class="brand-actions no-print">'
        f'<button type="button" class="btn-tool" id="mcp-theme-toggle" '
        f'title="Toggle light/dark theme (t)">Theme</button>'
        f'<button type="button" class="btn-tool" id="mcp-export-csv" '
        f'title="Download visible rows as CSV">Export CSV</button>'
        f'<button type="button" class="btn-pdf" id="mcp-export-pdf" '
        f'title="Print-friendly summary — choose Save as PDF in the dialog">'
        f'Save as PDF</button></div></div>'
    )


def _print_stylesheet_css() -> str:
    """Print layout for JMeter-style PDF export via browser or headless Chrome."""
    return """
@media print {
  :root { --bg0: #fff; --bg1: #f8fafc; --panel: #fff; --panel2: #f1f5f9; --border: #cbd5e1;
    --text: #0f172a; --muted: #475569; }
  body { background: #fff !important; color: #0f172a; font-size: 10pt; }
  .wrap { max-width: none; padding: 0; }
  .no-print, .filter-row, .filter-chips, .btn-pdf, .brand-nav { display: none !important; }
  .product-brand { border: none; box-shadow: none; padding: 0 0 0.75rem; margin-bottom: 0.5rem;
    border-bottom: 2px solid #6366f1; page-break-after: avoid; }
  .brand-link { color: #0f172a; text-decoration: none; }
  .brand-ver { color: #64748b; }
  .hero { padding: 0.5rem 0 1rem; page-break-after: avoid; }
  .stat-grid, .analytics-grid, .formats-strip, .quality, .feat-highlights,
  .toolkit-panel, .platform-panel, .portal-panel, .cov-panel, .tags-panel, .diag-panel {
    page-break-inside: avoid; break-inside: avoid;
  }
  .stat-card, .pie-wrap, .chart-card { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .srv-panels, .results-head { page-break-before: auto; }
  .file-block { page-break-inside: avoid; break-inside: avoid; }
  details.file-block { open: true; }
  table.results { font-size: 9pt; }
  td.detail pre { max-height: none; overflow: visible; }
  a { color: #2563eb; }
  footer { font-size: 8pt; margin-top: 1rem; border-top: 1px solid #e2e8f0; padding-top: 0.5rem; }
}
"""


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


def _preview_lines(text: str, *, max_lines: int = 7) -> str:
    """Trim reporter output for the formats strip (HTML-safe)."""
    lines = _strip_ansi(text).splitlines()
    if len(lines) <= max_lines:
        body = "\n".join(lines)
    else:
        body = "\n".join(lines[: max_lines - 1]) + "\n…"
    return _html_escape(body)


def _full_preview(text: str) -> str:
    return _html_escape(_strip_ansi(text))


def _formats_strip_html(results: SessionResults) -> str:
    """Showcase the four report formats using data from this run."""
    p, f, e, sk, t = _outcome_tally(results)
    total = p + f + e + sk + t
    fail_total = f + e + t
    dur_s = results.total_duration_ms / 1000.0

    console_raw = ConsoleReporter().generate(results)
    junit_raw = JUnitXMLReporter().generate(results)
    json_raw = JSONReporter().generate(results)

    console_preview = _preview_lines(console_raw)
    junit_preview = _preview_lines(junit_raw, max_lines=6)
    json_preview = _preview_lines(json_raw, max_lines=6)

    pass_pct = (100.0 * p / total) if total else 0.0
    html_preview = _html_escape(
        f"PASS {p} · FAIL {fail_total} · SKIP {sk}\n"
        f"Pass rate {pass_pct:.0f}% · {dur_s:.2f}s\n"
        f"Click to jump to charts & filters below"
    )

    cards: list[tuple[str, str, str, str, str, str | None]] = [
        (
            "Console",
            "Human-readable terminal output",
            console_preview,
            _full_preview(console_raw),
            "fmt-console",
            None,
        ),
        (
            "JUnit XML",
            "CI/CD integration",
            junit_preview,
            _full_preview(junit_raw),
            "fmt-junit",
            None,
        ),
        (
            "JSON",
            "Machine-readable data",
            json_preview,
            _full_preview(json_raw),
            "fmt-json",
            None,
        ),
        (
            "HTML Dashboard",
            "Rich visual reporting (this page)",
            html_preview,
            _html_escape(
                "Scroll to stat cards, charts, filters, and per-test results on this page."
            ),
            "fmt-html",
            "#mcp-stat-grid",
        ),
    ]
    chunks: list[str] = []
    for title, sub, preview, full_body, cls, jump_href in cards:
        if jump_href:
            chunks.append(
                f'<a class="fmt-card fmt-card-link {cls}" href="{jump_href}">'
                f'<div class="fmt-head">{_html_escape(title)} <span class="fmt-link-hint">↓ view below</span></div>'
                f'<div class="fmt-sub">{_html_escape(sub)}</div>'
                f'<div class="fmt-preview"><pre>{preview}</pre></div></a>'
            )
        else:
            chunks.append(
                f'<details class="fmt-card fmt-card-expand {cls}">'
                f'<summary class="fmt-card-sum">'
                f'<span class="fmt-head">{_html_escape(title)}</span>'
                f'<span class="fmt-sub">{_html_escape(sub)}</span>'
                f'<span class="fmt-expand-hint">Click for full output</span>'
                f'<div class="fmt-preview"><pre>{preview}</pre></div>'
                f"</summary>"
                f'<div class="fmt-full"><pre>{full_body}</pre></div>'
                f"</details>"
            )
    export_hint = (
        f'<p class="formats-export-hint">Export this run: '
        f'<code>mcp-test --report-format html --report-output report.html</code> '
        f'· <code>--report-format junit</code> · <code>--report-format json</code> '
        f'· <code>mcp-test export-pdf report.html</code></p>'
    )
    return (
        f'<section class="formats-strip" id="mcp-formats-strip">'
        f'<h2 class="section-title">Test report outputs</h2>'
        f'<p class="section-sub">One test run. Multiple formats. Complete visibility. '
        f'<span class="muted">Click a card to expand full Console, JUnit, or JSON output.</span></p>'
        f'<div class="fmt-grid">{"".join(chunks)}</div>{export_hint}</section>'
    )


def _stat_card_svg(kind: str) -> str:
    icons = {
        "pass": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M20 6L9 17l-5-5"/></svg>',
        "fail": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 6L6 18M6 6l12 12"/></svg>',
        "skip": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14"/></svg>',
        "time": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>',
    }
    return icons.get(kind, "")


def _summary_stat_cards(p: int, f: int, e: int, sk: int, t: int, total_ms: float) -> str:
    fail_total = f + e + t
    total_cases = p + fail_total + sk
    specs = (
        ("pass", "Passed", str(p), "sc-pass"),
        ("fail", "Failed", str(fail_total), "sc-fail"),
        ("skip", "Skipped", str(sk), "sc-skip"),
        ("time", "Duration", _format_duration_ms(total_ms), "sc-time"),
    )
    cards: list[str] = []
    val_ids = ("pass", "fail", "skip", None)
    for i, (kind, label, value, cls) in enumerate(specs):
        sid = val_ids[i]
        val_id = f' id="mcp-stat-{sid}"' if sid else ""
        cards.append(
            f'<div class="stat-card {cls}"><div class="stat-icon">{_stat_card_svg(kind)}</div>'
            f'<div class="stat-body"><div class="stat-label">{label}</div>'
            f'<div class="stat-value"{val_id}>{_html_escape(value)}</div></div></div>'
        )
    return (
        f'<div class="stat-grid" id="mcp-stat-grid" data-total="{total_cases}" '
        f'data-pass="{p}" data-fail="{f}" data-error="{e}" data-skip="{sk}" data-timeout="{t}">'
        f'{"".join(cards)}</div>'
    )


def _pie_legend_html(p: int, f: int, e: int, sk: int, t: int) -> str:
    tot = p + f + e + sk + t
    if tot == 0:
        return '<p class="muted">No tests ran.</p>'
    rows: list[str] = []
    for label, n, color in (
        ("Passed", p, "#1abc7a"),
        ("Failed", f, "#e74c3c"),
        ("Errors", e, "#f39c12"),
        ("Skipped", sk, "#7f8c8d"),
        ("Timeouts", t, "#9b59b6"),
    ):
        if n == 0:
            continue
        pct = 100.0 * n / tot
        rows.append(
            f'<div class="leg-row"><span class="leg-dot" style="background:{color}"></span>'
            f'<span class="leg-name">{label}</span>'
            f'<span class="leg-pct">{pct:.0f}%</span>'
            f'<span class="leg-n">{n}</span></div>'
        )
    return f'<div class="pie-legend">{"".join(rows)}</div>'


def _top_failures_html(results: SessionResults, limit: int = 6) -> str:
    bad = [
        tr
        for tr in results.test_results
        if tr.status in (CaseStatus.FAILED, CaseStatus.ERROR, CaseStatus.TIMEOUT)
    ]
    if not bad:
        return '<p class="muted good-note">No failing tests — quality gate clear.</p>'
    items: list[str] = []
    for tr in bad[:limit]:
        err = (tr.error or tr.assertion_diff or tr.status.value)[:120]
        items.append(
            f'<li class="fail-item"><span class="fail-name">{_html_escape(tr.name)}</span>'
            f'<span class="fail-badge b-{_status_class(tr.status)}">{_status_label(tr.status)}</span>'
            f'<div class="fail-msg">{_html_escape(err)}</div></li>'
        )
    extra = len(bad) - limit
    more = f'<li class="fail-more">+{extra} more</li>' if extra > 0 else ""
    return f'<ul class="fail-list">{"".join(items)}{more}</ul>'


def _duration_bars_html(results: SessionResults, limit: int = 8) -> str:
    ranked = sorted(results.test_results, key=lambda tr: tr.duration_ms, reverse=True)[:limit]
    if not ranked:
        return '<p class="muted">—</p>'
    max_ms = max(tr.duration_ms for tr in ranked) or 1.0
    bars: list[str] = []
    for tr in ranked:
        w = 100.0 * tr.duration_ms / max_ms
        cls = _status_class(tr.status)
        bars.append(
            f'<div class="dur-row"><div class="dur-label" title="{_html_escape(tr.name)}">'
            f'{_html_escape(tr.name[:36])}</div>'
            f'<div class="dur-track"><div class="dur-fill dur-{cls}" style="width:{w:.1f}%"></div></div>'
            f'<div class="dur-ms">{tr.duration_ms:.0f}ms</div></div>'
        )
    return f'<div class="dur-chart">{"".join(bars)}</div>'


def _run_timeline_svg(results: SessionResults) -> str:
    """Cumulative pass-rate line across tests in run order."""
    tests = results.test_results
    if not tests:
        return '<svg class="timeline-svg" viewBox="0 0 320 120" aria-hidden="true"><text x="8" y="60" fill="#64748b" font-size="11">No data</text></svg>'
    w, h, pad = 320, 120, 24
    n = len(tests)
    pts: list[str] = []
    passed = 0
    for i, tr in enumerate(tests):
        if tr.status == CaseStatus.PASSED:
            passed += 1
        rate = 100.0 * passed / (i + 1)
        x = pad + (w - 2 * pad) * i / max(n - 1, 1)
        y = h - pad - (h - 2 * pad) * rate / 100.0
        pts.append(f"{x:.1f},{y:.1f}")
    poly = " ".join(pts)
    area = f"{pad},{h - pad} {poly} {w - pad},{h - pad}"
    return (
        f'<svg class="timeline-svg" viewBox="0 0 {w} {h}" role="img" '
        f'aria-label="Cumulative pass rate across tests">'
        f'<defs><linearGradient id="tg" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="#1abc7a" stop-opacity="0.35"/>'
        f'<stop offset="100%" stop-color="#1abc7a" stop-opacity="0"/></linearGradient></defs>'
        f'<polygon points="{area}" fill="url(#tg)"/>'
        f'<polyline points="{poly}" fill="none" stroke="#1abc7a" stroke-width="2.5" stroke-linecap="round"/>'
        f'</svg>'
    )


def _analytics_dashboard_html(
    results: SessionResults, pass_pct: float, pie_style: str
) -> str:
    p, f, e, sk, t = _outcome_tally(results)
    pct_label = f"{pass_pct:.0f}%" if (p + f + e + sk + t) else "—"
    return (
        f'<section class="analytics">'
        f'<div class="analytics-card chart-card">'
        f'<h3>Pass rate</h3>'
        f'<div class="donut-wrap">'
        f'<div class="donut-outer" style="background:{pie_style}">'
        f'<div class="donut-inner"><span class="donut-pct">{_html_escape(pct_label)}</span>'
        f'<span class="donut-sub">pass rate</span></div></div>'
        f'{_pie_legend_html(p, f, e, sk, t)}'
        f'</div></div>'
        f'<div class="analytics-card">'
        f'<h3>Run timeline</h3>'
        f'<p class="chart-hint">Cumulative pass rate across tests in execution order</p>'
        f'{_run_timeline_svg(results)}'
        f'</div>'
        f'<div class="analytics-card">'
        f'<h3>Top failing tests</h3>'
        f'{_top_failures_html(results)}'
        f'</div>'
        f'<div class="analytics-card">'
        f'<h3>Slowest tests</h3>'
        f'{_duration_bars_html(results)}'
        f'</div>'
        f'</section>'
    )


def _feature_chip(label: str, value: str, cls: str = "") -> str:
    return (
        f'<div class="feat-chip {cls}"><span class="feat-val">{_html_escape(value)}</span>'
        f'<span class="feat-lbl">{_html_escape(label)}</span></div>'
    )


def _feature_highlights_html(results: SessionResults) -> str:
    tests = results.test_results
    if not tests:
        return ""
    sec_tags = frozenset({"security", "sec"})
    perf_tags = frozenset({"perf", "performance", "latency", "throughput"})
    res_tags = frozenset({"resiliency", "resilience", "chaos"})

    def _has_tag(tr: CaseResult, keys: frozenset[str]) -> bool:
        return bool({t.lower() for t in tr.tags} & keys)

    n_security = sum(1 for tr in tests if _has_tag(tr, sec_tags))
    n_perf = sum(1 for tr in tests if _has_tag(tr, perf_tags))
    n_res = sum(1 for tr in tests if _has_tag(tr, res_tags))
    n_trace = sum(1 for tr in tests if tr.mcp_trace and tr.mcp_trace.get("events"))
    n_flaky = sum(1 for tr in tests if tr.flaky)
    n_schema = sum(1 for tr in tests if tr.schema_violations)
    n_tags = len({t for tr in tests for t in tr.tags})

    chips = [
        _feature_chip("Security tests", str(n_security), "feat-sec"),
        _feature_chip("Performance", str(n_perf), "feat-perf"),
        _feature_chip("Resiliency / chaos", str(n_res), "feat-res"),
        _feature_chip("MCP traces", str(n_trace), "feat-trace"),
        _feature_chip("Flaky (retried)", str(n_flaky), "feat-flaky"),
        _feature_chip("Schema checks", str(n_schema), "feat-schema"),
        _feature_chip("Unique tags", str(n_tags), "feat-tags"),
    ]
    return (
        f'<section class="feat-highlights"><h2 class="section-title">Harness features in this run</h2>'
        f'<p class="section-sub">Security payloads, performance SLOs, chaos, traces, schema validation, and more.</p>'
        f'<div class="feat-grid">{"".join(chips)}</div></section>'
    )


def _cov_bar(tested: int, total: int) -> str:
    pct = (100.0 * tested / total) if total else 0.0
    return (
        f'<div class="cov-bar-track"><div class="cov-bar-fill" style="width:{pct:.0f}%"></div></div>'
        f'<span class="cov-bar-pct">{tested}/{total}</span>'
    )


def _cov_chips(items: list[str], tested_set: set[str], *, limit: int = 12) -> str:
    if not items:
        return '<span class="muted">none advertised</span>'
    chips: list[str] = []
    for name in items[:limit]:
        ok = name in tested_set
        cls = "cov-ok" if ok else "cov-gap"
        mark = "&#10003;" if ok else "!"
        chips.append(
            f'<span class="cov-chip {cls}" title="{"tested" if ok else "not tested"}">'
            f'{mark} {_html_escape(name)}</span>'
        )
    extra = len(items) - limit
    if extra > 0:
        chips.append(f'<span class="cov-chip cov-more">+{extra}</span>')
    return "".join(chips)


def _coverage_inventory_html(results: SessionResults) -> str:
    cov = results.coverage or {}
    if not cov:
        return ""
    adv = cov.get("advertised", {})
    tst = cov.get("tested", {})
    gaps = cov.get("gaps", {})
    summary = cov.get("summary", {})
    tested_tools = set(tst.get("tools", []))
    tested_res = set(tst.get("resources", []))
    tested_pr = set(tst.get("prompts", []))
    auth_tools = set(tst.get("auth_tools", []))

    blocks: list[str] = []
    for title, ad_list, tested_set, gap_key in (
        ("Tools", adv.get("tools", []), tested_tools, "untested_tools"),
        ("Resources", adv.get("resources", []), tested_res, "untested_resources"),
        ("Prompts", adv.get("prompts", []), tested_pr, "untested_prompts"),
    ):
        gap_names = gaps.get(gap_key, [])
        blocks.append(
            f'<div class="cov-block"><div class="cov-head">'
            f'<span>{_html_escape(title)}</span>{_cov_bar(len(tested_set), len(ad_list))}</div>'
            f'<div class="cov-chips">{_cov_chips(ad_list, tested_set)}</div>'
            + (
                f'<p class="cov-gap-note">{len(gap_names)} untested</p>'
                if gap_names
                else '<p class="cov-gap-note cov-ok-note">full coverage</p>'
            )
            + "</div>"
        )

    missing_auth = gaps.get("tools_missing_auth_tests", [])
    auth_line = ""
    if tested_tools:
        auth_line = (
            f'<p class="cov-auth">Auth boundary tests: <strong>{len(auth_tools)}</strong> of '
            f'<strong>{len(tested_tools)}</strong> exercised tools'
            + (f' &middot; <span class="cov-warn">{len(missing_auth)} missing</span>' if missing_auth else "")
            + "</p>"
        )

    return (
        f'<section class="cov-panel"><h2 class="section-title">MCP inventory coverage</h2>'
        f'<p class="section-sub">Advertised vs exercised tools, resources, and prompts (coverage map).</p>'
        f'{auth_line}<div class="cov-blocks">{"".join(blocks)}</div></section>'
    )


def _tags_matrix_html(results: SessionResults) -> str:
    stats: dict[str, dict[str, int]] = defaultdict(lambda: {"pass": 0, "fail": 0, "skip": 0})
    for tr in results.test_results:
        tags = tr.tags if tr.tags else ["(untagged)"]
        bucket = "pass" if tr.status == CaseStatus.PASSED else (
            "skip" if tr.status == CaseStatus.SKIPPED else "fail"
        )
        for tg in tags:
            stats[tg][bucket] += 1
    if not stats:
        return ""
    rows: list[str] = []
    for tag in sorted(stats.keys()):
        s = stats[tag]
        total = s["pass"] + s["fail"] + s["skip"]
        rate = (100.0 * s["pass"] / total) if total else 0
        bar_w = rate
        rows.append(
            f'<tr><td><span class="tagchip">{_html_escape(tag)}</span></td>'
            f'<td class="num">{s["pass"]}</td><td class="num fail-n">{s["fail"]}</td>'
            f'<td class="num">{s["skip"]}</td>'
            f'<td><div class="tag-bar"><div class="tag-bar-fill" style="width:{bar_w:.0f}%"></div></div>'
            f'<span class="tag-rate">{rate:.0f}%</span></td></tr>'
        )
    return (
        f'<section class="tags-panel"><h2 class="section-title">Results by tag</h2>'
        f'<p class="section-sub">security, perf, chaos, smoke — pass rate per marker category.</p>'
        f'<div class="tags-table-wrap"><table class="tags-table"><thead><tr>'
        f'<th>Tag</th><th>Pass</th><th>Fail</th><th>Skip</th><th>Pass rate</th>'
        f'</tr></thead><tbody>{"".join(rows)}</tbody></table></div></section>'
    )


def _slug_id(name: str) -> str:
    slug = "".join(c if c.isalnum() else "-" for c in name.lower()).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug[:48] or "test"


def _diagnostics_panel_html(results: SessionResults) -> str:
    flaky = [tr for tr in results.test_results if tr.flaky]
    schema = [tr for tr in results.test_results if tr.schema_violations]
    traced = [
        tr for tr in results.test_results
        if tr.mcp_trace and tr.mcp_trace.get("events")
    ]
    if not flaky and not schema and not traced:
        return ""

    chunks: list[str] = []
    if flaky:
        items = "".join(
            f'<li><a href="#test-{_slug_id(tr.name)}">{_html_escape(tr.name)}</a>'
            f' <span class="muted">({tr.retry_count} retries)</span></li>'
            for tr in flaky
        )
        chunks.append(f'<div class="diag-col"><h4>Flaky tests</h4><ul class="diag-list">{items}</ul></div>')
    if schema:
        items = "".join(
            f'<li><a href="#test-{_slug_id(tr.name)}">{_html_escape(tr.name)}</a>'
            f' <span class="muted">{len(tr.schema_violations)} violation(s)</span></li>'
            for tr in schema
        )
        chunks.append(f'<div class="diag-col"><h4>Schema violations</h4><ul class="diag-list">{items}</ul></div>')
    if traced:
        items = "".join(
            f'<li><a href="#test-{_slug_id(tr.name)}">{_html_escape(tr.name)}</a>'
            f' <span class="muted">{tr.mcp_trace.get("event_count", 0)} events</span></li>'
            for tr in traced
        )
        chunks.append(f'<div class="diag-col"><h4>MCP JSON-RPC traces</h4><ul class="diag-list">{items}</ul></div>')

    return (
        f'<section class="diag-panel"><h2 class="section-title">Diagnostics</h2>'
        f'<p class="section-sub">Jump to flaky retries, schema drift, and per-test MCP trace timelines.</p>'
        f'<div class="diag-cols">{"".join(chunks)}</div></section>'
    )


_BASTION_REPO = "https://github.com/vaquarkhan/MCP-Bastion"
_BASTION_PYPI = "https://pypi.org/project/mcp-bastion-python/"

_CHAOS_FAULT_LEGEND: tuple[tuple[str, str], ...] = (
    ("delay", "Inject latency before tool responses"),
    ("503", "Simulate gateway / transport unavailable"),
    ("truncate", "Return partial tool result payloads"),
    ("schema_drift", "Mutate response shape to probe clients"),
)


def _chaos_faults_from_tags(tags: list[str]) -> list[str]:
    faults: list[str] = []
    for tag in tags:
        low = tag.lower()
        if low == "chaos":
            continue
        if low.startswith("chaos:"):
            faults.append(low.split(":", 1)[1])
        elif low in ("delay", "503", "truncate", "schema_drift", "schema-drift", "drift"):
            faults.append(low.replace("-", "_"))
    if not faults and any(t.lower() == "chaos" for t in tags):
        faults.append("delay")
    return faults


def _optional_bastion_version(env: dict[str, str]) -> str | None:
    if env.get("bastion_version"):
        return str(env["bastion_version"])
    try:
        import importlib.metadata

        return importlib.metadata.version("mcp-bastion-python")
    except Exception:
        return None


def _chaos_monkey_panel_html(results: SessionResults) -> str:
    chaos_tests = [
        tr
        for tr in results.test_results
        if "chaos" in {t.lower() for t in tr.tags}
        or any(t.lower().startswith("chaos:") for t in tr.tags)
    ]
    if not chaos_tests:
        return ""

    legend = "".join(
        f'<span class="chaos-pill" title="{_html_escape(desc)}">{_html_escape(name)}</span>'
        for name, desc in _CHAOS_FAULT_LEGEND
    )
    rows: list[str] = []
    for tr in chaos_tests:
        faults = _chaos_faults_from_tags(tr.tags)
        fault_txt = ", ".join(faults) if faults else "delay"
        cls = _status_class(tr.status)
        rows.append(
            f'<tr><td><a href="#test-{_slug_id(tr.name)}">{_html_escape(tr.name)}</a></td>'
            f'<td><code class="chaos-faults">{_html_escape(fault_txt)}</code></td>'
            f'<td><span class="badge b-{cls}">{_status_label(tr.status)}</span></td>'
            f'<td class="num">{tr.duration_ms:.0f}ms</td></tr>'
        )
    passed = sum(1 for tr in chaos_tests if tr.status == CaseStatus.PASSED)
    return (
        f'<section class="chaos-panel platform-panel">'
        f'<h2 class="section-title">Chaos monkey</h2>'
        f'<p class="section-sub">Protocol-aware faults on <code>call_tool</code> '
        f'(<code>@marker(tags=[&quot;chaos&quot;], chaos_faults=[...])</code>) — '
        f'{passed}/{len(chaos_tests)} survived.</p>'
        f'<div class="chaos-legend">{legend}</div>'
        f'<table class="platform-table"><thead><tr>'
        f'<th>Test</th><th>Faults injected</th><th>Outcome</th><th>Duration</th>'
        f'</tr></thead><tbody>{"".join(rows)}</tbody></table></section>'
    )


def _performance_load_panel_html(results: SessionResults) -> str:
    perf_tags = frozenset({"perf", "performance", "latency", "throughput", "load"})
    perf_tests = [
        tr for tr in results.test_results
        if {t.lower() for t in tr.tags} & perf_tags
        or "latency" in tr.name.lower()
        or "throughput" in tr.name.lower()
        or "rps" in (tr.error or "").lower()
    ]
    durs = [
        tr.duration_ms for tr in results.test_results
        if tr.status != CaseStatus.SKIPPED
    ]
    pcts = _suite_duration_percentiles(durs)

    pct_cards = "".join(
        f'<div class="pct-card"><div class="pct-k">{k.replace("_ms", "").upper()}</div>'
        f'<div class="pct-v">{v:.1f}<span class="pct-u">ms</span></div></div>'
        for k, v in pcts.items()
    )

    rows: list[str] = []
    for tr in perf_tests:
        note = ""
        err = tr.error or ""
        if "rps" in err.lower() or "p99" in err.lower() or "throughput" in err.lower():
            note = f'<div class="slo-hint">{_html_escape(err[:100])}</div>'
        elif "p95" in err.lower() or "latency" in err.lower():
            note = f'<div class="slo-hint">{_html_escape(err[:100])}</div>'
        cls = _status_class(tr.status)
        rows.append(
            f'<tr><td><a href="#test-{_slug_id(tr.name)}">{_html_escape(tr.name)}</a></td>'
            f'<td>{", ".join(_html_escape(t) for t in tr.tags) or "—"}</td>'
            f'<td><span class="badge b-{cls}">{_status_label(tr.status)}</span></td>'
            f'<td class="num">{tr.duration_ms:.0f}ms</td>'
            f'<td>{note}</td></tr>'
        )

    load_note = (
        '<p class="muted load-note"><code>assert_throughput</code> exercises concurrent '
        '<code>call_tool</code> with <code>min_rps</code>, <code>max_p99_ms</code>, '
        'and <code>max_error_rate</code> gates.</p>'
    )
    table = (
        f'<table class="platform-table"><thead><tr>'
        f'<th>Test</th><th>Tags</th><th>Outcome</th><th>Duration</th><th>SLO note</th>'
        f'</tr></thead><tbody>{"".join(rows)}</tbody></table>'
        if rows
        else '<p class="muted">No performance-tagged tests in this run.</p>'
    )
    return (
        f'<section class="perf-panel platform-panel">'
        f'<h2 class="section-title">Load &amp; performance SLOs</h2>'
        f'<p class="section-sub">Suite duration percentiles plus '
        f'<code>assert_latency</code> / <code>assert_throughput</code> / baseline checks.</p>'
        f'<div class="pct-grid">{pct_cards}</div>{load_note}{table}</section>'
    )


def _security_bastion_panel_html(results: SessionResults) -> str:
    findings = build_security_findings(results)
    bastion_ver = _optional_bastion_version(results.environment)
    bastion_paired = results.environment.get("bastion_paired", "")

    finding_rows: list[str] = []
    for f in findings[:8]:
        rule = f.get("rule") or {}
        rule_id = str(rule.get("id", ""))
        sev = str(rule.get("severity", "medium")).upper()
        sev_cls = "sev-high" if sev == "HIGH" else "sev-med"
        tname = str(f.get("test_name", ""))
        finding_rows.append(
            f'<li class="finding-item {sev_cls}">'
            f'<span class="finding-rule">{_html_escape(rule_id)}</span> '
            f'<span class="finding-sev">{sev}</span><br>'
            f'<a href="#test-{_slug_id(tname)}">{_html_escape(tname)}</a>'
            f'<div class="finding-msg">{_html_escape(str(f.get("message", ""))[:120])}</div></li>'
        )
    findings_block = (
        f'<ul class="findings-list">{"".join(finding_rows)}</ul>'
        if finding_rows
        else '<p class="good-note">No OWASP-tagged security failures in this run.</p>'
    )

    bastion_status = (
        f'Installed <code>mcp-bastion-python {_html_escape(bastion_ver)}</code>'
        if bastion_ver
        else "Not detected in this CI environment"
    )
    if bastion_paired:
        bastion_status += f' &middot; {_html_escape(bastion_paired)}'

    pairing_rows = (
        ("Prompt injection", "assert_injection_blocked", "PromptGuard middleware"),
        ("PII / secrets", "assert_no_secret_leak", "Presidio redaction"),
        ("Auth boundaries", "assert_authorization_boundary", "RBAC + tool policies"),
        ("Rate limits", "assert_throughput SLOs", "Token budgets &amp; iteration caps"),
        ("Path traversal", "assert_path_traversal_blocked", "Policy-as-code rules"),
    )
    pair_table = "".join(
        f'<tr><td>{_html_escape(ci)}</td><td><code>{ci_assert}</code></td>'
        f'<td class="bastion-col">{bastion}</td></tr>'
        for ci, ci_assert, bastion in pairing_rows
    )

    return (
        f'<section class="bastion-panel platform-panel">'
        f'<h2 class="section-title">Security findings &amp; MCP-Bastion pairing</h2>'
        f'<p class="section-sub">Test defenses in CI with the harness; enforce at runtime with '
        f'<a href="{_BASTION_REPO}" target="_blank" rel="noopener">MCP-Bastion</a>.</p>'
        f'<div class="bastion-split">'
        f'<div class="bastion-col-card ci-card">'
        f'<h3>CI gate (this report)</h3>'
        f'<p class="bastion-ver">{bastion_status}</p>'
        f'{findings_block}'
        f'<p class="bastion-cta muted">Export SARIF: <code>mcp-test --sarif-output findings.sarif</code></p>'
        f'</div>'
        f'<div class="bastion-col-card prod-card">'
        f'<h3>Production (MCP-Bastion)</h3>'
        f'<table class="pair-table"><thead><tr><th>Threat</th><th>Harness verifies</th>'
        f'<th>Bastion enforces</th></tr></thead><tbody>{pair_table}</tbody></table>'
        f'<p class="bastion-install">'
        f'<code>pip install mcp-bastion-python</code> &middot; '
        f'<a href="{_BASTION_PYPI}" target="_blank" rel="noopener">PyPI</a></p>'
        f'</div></div></section>'
    )


def _platform_toolkit_grid_html(results: SessionResults) -> str:
    """Capability cards for major harness features exercised in this run."""
    tests = results.test_results
    tag_sets = [{t.lower() for t in tr.tags} for tr in tests]

    def _count_tag(*keys: str) -> int:
        kset = frozenset(keys)
        return sum(1 for tr in tests if {t.lower() for t in tr.tags} & kset)

    cards = [
        ("Chaos monkey", _count_tag("chaos") or sum(1 for ts in tag_sets if any(t.startswith("chaos:") for t in ts)), "delay · 503 · truncate · drift", "toolkit-chaos"),
        ("Load / throughput", _count_tag("perf", "performance", "throughput", "load", "latency"), "assert_latency · assert_throughput", "toolkit-perf"),
        ("Security payloads", _count_tag("security", "sec"), "injection · traversal · secrets", "toolkit-sec"),
        ("Resiliency", _count_tag("resiliency", "resilience"), "degrades · reconnect · crash", "toolkit-res"),
        ("Regression", _count_tag("regression", "snapshot"), "assert_snapshot · idempotent", "toolkit-reg"),
        ("MCP trace", sum(1 for tr in tests if tr.mcp_trace), "per-test JSON-RPC timeline", "toolkit-trace"),
    ]
    chips = "".join(
        f'<div class="toolkit-card {css}"><div class="toolkit-n">{n}</div>'
        f'<div class="toolkit-title">{_html_escape(title)}</div>'
        f'<div class="toolkit-sub">{_html_escape(sub)}</div></div>'
        for title, n, sub, css in cards
    )
    return (
        f'<section class="toolkit-panel"><h2 class="section-title">Platform QA toolkit</h2>'
        f'<p class="section-sub">Features exercised in this run — chaos, load, security, resiliency, regression, trace.</p>'
        f'<div class="toolkit-grid">{chips}</div></section>'
    )


def _conformance_panel_html(results: SessionResults) -> str:
    """HTML card for RFC-002 conformance level."""
    us = results.unified_summary or {}
    conf = us.get("conformance")
    if not conf:
        return ""
    name = conf.get("name", "—")
    level = conf.get("level", "—")
    levels = conf.get("levels") or {}
    pills = "".join(
        f'<span class="conf-pill {"conf-yes" if levels.get(k) else "conf-no"}">{_html_escape(k)}</span>'
        for k in ("boot", "protocol", "covered", "secure", "resilient")
    )
    reasons = conf.get("reasons") or []
    reason_html = ""
    if reasons:
        reason_html = (
            "<ul class=\"conf-reasons\">"
            + "".join(f"<li>{_html_escape(r)}</li>" for r in reasons[:6])
            + "</ul>"
        )
    badge_url = (conf.get("badge") or {}).get("url") or ""
    badge_img = (
        f'<img class="conf-badge" src="{_html_escape(badge_url)}" '
        f'alt="mcp-test {_html_escape(str(name))}" />'
        if badge_url
        else ""
    )
    return (
        f'<section class="conformance-panel platform-panel">'
        f'<h2 class="section-title">Conformance</h2>'
        f'<p class="section-sub">RFC-002 seal — <strong>{_html_escape(str(name))}</strong> '
        f'(level {_html_escape(str(level))})</p>'
        f'<div class="conf-row">{badge_img}<div class="conf-pills">{pills}</div></div>'
        f"{reason_html}</section>"
    )


def _unified_portal_html(results: SessionResults) -> str:
    """HTML block for functional / perf / security / resiliency scores + coverage."""
    us = results.unified_summary
    if not us:
        return ""
    cats = us.get("categories", {})
    labels = (
        ("functional", "Functional"),
        ("performance", "Performance"),
        ("security", "Security"),
        ("resiliency", "Resiliency"),
    )
    cards: list[str] = []
    for key, label in labels:
        c = cats.get(key, {})
        score = c.get("score_pct")
        status = c.get("status", "n/a")
        total = c.get("total", 0)
        score_txt = f"{score}%" if score is not None else "—"
        cls = "portal-pass" if status == "pass" else ("portal-fail" if status == "fail" else "portal-na")
        cards.append(
            f'<div class="portal-card {cls}"><div class="portal-label">{_html_escape(label)}</div>'
            f'<div class="portal-score">{_html_escape(score_txt)}</div>'
            f'<div class="portal-sub">{total} test(s) · {_html_escape(status)}</div></div>'
        )
    cov_line = ""
    if us.get("coverage_headline"):
        cov_line = f'<p class="portal-cov">{_html_escape(str(us["coverage_headline"]))}</p>'
    gaps = (results.coverage or {}).get("gaps", {})
    gap_bits: list[str] = []
    for tool in gaps.get("untested_tools", [])[:6]:
        gap_bits.append(f"<li>untested tool: <code>{_html_escape(tool)}</code></li>")
    for tool in gaps.get("tools_missing_auth_tests", [])[:6]:
        gap_bits.append(f"<li>missing auth test: <code>{_html_escape(tool)}</code></li>")
    gaps_html = ""
    if gap_bits:
        gaps_html = f'<ul class="portal-gaps">{"".join(gap_bits)}</ul>'
    return (
        f'<section class="portal"><h2>Unified test portal</h2>'
        f'<div class="portal-grid">{"".join(cards)}</div>{cov_line}{gaps_html}</section>'
    )


def _experiments_scorecard_html(results: SessionResults) -> str:
    """HTML panel for resiliency experiment scorecard."""
    us = results.unified_summary or {}
    scorecard = us.get("experiments")
    if not scorecard or not scorecard.get("experiments"):
        return ""
    grade = scorecard.get("grade", "n/a")
    score = scorecard.get("score_pct")
    score_txt = f"{score}%" if score is not None else "—"
    rows: list[str] = []
    for entry in scorecard.get("experiments") or []:
        status = entry.get("status", "?")
        exp_id = entry.get("id", "")
        title = entry.get("title", exp_id)
        hypo = entry.get("hypothesis", "")
        cls = "portal-pass" if status == "passed" else ("portal-fail" if status in ("failed", "aborted") else "portal-na")
        cmd = f"mcp-test experiment run {exp_id}"
        rows.append(
            f'<tr class="{cls}"><td><code>{_html_escape(exp_id)}</code></td>'
            f'<td>{_html_escape(title)}</td>'
            f'<td>{_html_escape(status)}</td>'
            f'<td class="exp-hypo">{_html_escape(hypo)}</td>'
            f'<td><button type="button" class="copy-cmd" data-cmd="{_html_escape(cmd)}">Copy run</button></td></tr>'
        )
    return (
        f'<section class="experiments-panel platform-panel"><h2 class="section-title">Resiliency experiments</h2>'
        f'<p class="section-sub">Curated fault-injection templates — grade <strong>{_html_escape(str(grade))}</strong> '
        f'({_html_escape(score_txt)}).</p>'
        f'<table class="exp-table"><thead><tr><th>Id</th><th>Title</th><th>Status</th>'
        f'<th>Hypothesis</th><th></th></tr></thead><tbody>{"".join(rows)}</tbody></table></section>'
    )


def _trace_timeline_html(tr: CaseResult) -> str:
    """Render MCP JSON-RPC trace as a compact timeline block."""
    trace = tr.mcp_trace
    if not trace or not trace.get("events"):
        return ""
    rows: list[str] = []
    for ev in trace["events"]:
        direction = ev.get("direction", "?")
        method = ev.get("method", "?")
        t_ms = ev.get("t_ms", 0)
        nbytes = ev.get("bytes", 0)
        cls = f"trace-{direction}"
        poll = ' <span class="pollution">stdio pollution?</span>' if ev.get("stdio_pollution") else ""
        payload = ev.get("payload")
        preview = _html_escape(str(payload)[:500]) if payload is not None else ""
        rows.append(
            f'<div class="trace-row {cls}">'
            f'<span class="trace-t">{t_ms}ms</span>'
            f'<span class="trace-dir">{_html_escape(direction)}</span>'
            f'<span class="trace-method">{_html_escape(method)}</span>'
            f'<span class="trace-bytes">{nbytes} B</span>{poll}'
            f'<pre class="trace-payload">{preview}</pre></div>'
        )
    pollution = trace.get("stdio_pollution") or []
    pol_html = ""
    if pollution:
        pol_html = (
            '<p class="pollution-head">Possible stdio pollution:</p><ul>'
            + "".join(f"<li><code>{_html_escape(p)}</code></li>" for p in pollution)
            + "</ul>"
        )
    return (
        f'<div class="trace-block"><h4>MCP trace ({trace.get("event_count", len(trace["events"]))} events)</h4>'
        f"{pol_html}{''.join(rows)}</div>"
    )


class HTMLReporter:
    """Generate a self-contained HTML test report."""

    def generate(self, results: SessionResults) -> str:
        p, f, e, sk, t = _outcome_tally(results)
        total_cases = p + f + e + sk + t
        us_gate = (results.unified_summary or {}).get("quality_gate") or {}
        qg_status = us_gate.get("status")
        if qg_status in ("pass", "fail", "n/a"):
            ok = qg_status == "pass"
            if qg_status == "pass" and total_cases > 0:
                gate = "QUALITY GATE: PASSED"
            elif qg_status == "fail":
                reasons = us_gate.get("reasons") or []
                suffix = f" — {'; '.join(reasons[:2])}" if reasons else ""
                gate = f"QUALITY GATE: FAILED{suffix}"
            else:
                gate = "QUALITY GATE: N/A (no cases)"
        else:
            ok = _quality_ok(results)
            gate = "QUALITY GATE: PASSED" if ok and total_cases > 0 else (
                "QUALITY GATE: FAILED" if not ok else "QUALITY GATE: N/A (no cases)"
            )
        exit_badge = "RUN PASSED" if ok and total_cases else ("RUN FAILED" if not ok else "NO TESTS")
        pass_pct = (100.0 * p / total_cases) if total_cases else 0.0
        pie_style = _conic_gradient_pie_style(results)
        h_ver = _html_escape(str(results.harness_version or ""))
        proto = _html_escape(str(results.protocol_version or ""))
        cap_preview = _html_escape(_summarize_caps(results.server_capabilities))
        total_ms = f"{results.total_duration_ms:.1f}"
        proto_line = f"<br>Protocol {proto}" if proto else ""
        run_start = _html_escape(results.started_at or "—")
        run_end = _html_escape(results.finished_at or "—")
        run_start_ms, run_end_ms = _run_epoch_bounds(results)
        run_start_ms_js = str(run_start_ms) if run_start_ms is not None else "null"
        run_end_ms_js = str(run_end_ms) if run_end_ms is not None else "null"
        env_lines = []
        for key in ("python_version", "platform", "cwd", "server_command", "transport"):
            val = results.environment.get(key, "")
            if val:
                env_lines.append(
                    f"<li><strong>{_html_escape(key)}</strong> "
                    f"<code>{_html_escape(str(val))}</code></li>"
                )
        env_block = f"<ul class=\"env-list\">{''.join(env_lines)}</ul>" if env_lines else "<p class=\"muted\">—</p>"

        by_file: dict[str, list[CaseResult]] = defaultdict(list)
        for tr in results.test_results:
            by_file[_display_file(tr)].append(tr)
        # Stable order: sorted path
        file_order = sorted(by_file.keys())

        row_chunks: list[str] = []
        for fp in file_order:
            group = by_file[fp]
            n = len(group)
            inner_rows: list[str] = []
            for tr in group:
                inner_rows.append(self._one_row(tr))
            row_chunks.append(
                f'<details class="file-block" open><summary class="file-sum">'
                f"{_html_escape(fp)} <span class=\"n\">({n})</span></summary>"
                f'<div class="inner-table"><table class="results"><thead><tr>'
                f'<th>Test</th><th>Tags</th><th class="mcp-sort-started" data-dir="1" '
                f'title="Click to sort by start time">Started</th><th>Status</th>'
                f'<th class="mcp-sort-dur" data-dir="1" title="Click to sort by duration">Duration</th>'
                f'<th>Details</th></tr></thead><tbody>{"".join(inner_rows)}</tbody></table></div></details>'
            )

        body_main = "\n".join(row_chunks) if row_chunks else "<p class=\"muted\">No test results.</p>"

        portal_html = _unified_portal_html(results)
        experiments_html = _experiments_scorecard_html(results)
        conformance_html = _conformance_panel_html(results)
        formats_html = _formats_strip_html(results)
        stat_cards = _summary_stat_cards(p, f, e, sk, t, results.total_duration_ms)
        analytics_html = _analytics_dashboard_html(results, pass_pct, pie_style)
        features_html = _feature_highlights_html(results)
        coverage_html = _coverage_inventory_html(results)
        tags_html = _tags_matrix_html(results)
        diagnostics_html = _diagnostics_panel_html(results)
        toolkit_html = _platform_toolkit_grid_html(results)
        chaos_html = _chaos_monkey_panel_html(results)
        perf_html = _performance_load_panel_html(results)
        bastion_html = _security_bastion_panel_html(results)
        brand_html = _product_brand_bar_html(h_ver)
        print_css = _print_stylesheet_css()
        site_esc = _html_escape(PRODUCT_SITE)

        badge_class = "exit-pass" if ok and total_cases else ("exit-fail" if not ok else "exit-neu")
        gate_cls = "ok" if ok and total_cases else ("bad" if not ok else "neutral")

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="dark">
<title>MCP Test Report</title>
<style>
:root {{
  --bg0: #070b12;
  --bg1: #0d1320;
  --panel: #121a2b;
  --panel2: #1a2438;
  --border: #2a3650;
  --text: #eef2f7;
  --muted: #8fa3bf;
  --accent: #3b82f6;
  --glow: rgba(59,130,246,.15);
  --c-pass: #22c55e;
  --c-fail: #ef4444;
  --c-err: #f59e0b;
  --c-skip: #94a3b8;
  --c-to: #a855f7;
  --radius: 14px;
  --shadow: 0 8px 32px rgba(0,0,0,.45);
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  font-family: "Segoe UI", Inter, system-ui, -apple-system, sans-serif;
  background: radial-gradient(ellipse 120% 80% at 50% -20%, #1a2a4a 0%, var(--bg0) 55%);
  color: var(--text);
  min-height: 100vh;
  line-height: 1.5;
}}
.wrap {{ max-width: 1280px; margin: 0 auto; padding: 1.25rem 1rem 2.5rem; }}
.hero {{
  text-align: center;
  padding: 2rem 1rem 1.5rem;
  margin-bottom: 1.25rem;
  border-radius: var(--radius);
  background: linear-gradient(135deg, rgba(59,130,246,.12) 0%, rgba(34,197,94,.08) 100%);
  border: 1px solid var(--border);
  box-shadow: var(--shadow);
}}
.hero h1 {{
  margin: 0;
  font-size: clamp(1.6rem, 4vw, 2.4rem);
  font-weight: 800;
  letter-spacing: -0.02em;
  background: linear-gradient(90deg, #fff 0%, #93c5fd 50%, #6ee7b7 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}}
.hero .tagline {{ color: var(--muted); margin: 0.5rem 0 1rem; font-size: 1rem; }}
.hero-meta {{
  display: flex; flex-wrap: wrap; gap: 0.75rem 1.25rem; justify-content: center;
  align-items: center; font-size: 0.8rem; color: var(--muted);
}}
.badge-top {{
  display: inline-block; padding: 0.45rem 1rem; border-radius: 999px;
  font-weight: 800; font-size: 0.85rem; letter-spacing: 0.06em;
}}
.exit-pass {{ background: rgba(34,197,94,.2); color: #4ade80; border: 1px solid rgba(34,197,94,.45); }}
.exit-fail {{ background: rgba(239,68,68,.18); color: #f87171; border: 1px solid rgba(239,68,68,.4); }}
.exit-neu {{ background: var(--panel2); color: var(--muted); border: 1px solid var(--border); }}
.section-title {{ margin: 0 0 0.25rem; font-size: 1.1rem; font-weight: 700; color: #e2e8f0; }}
.section-sub {{ margin: 0 0 1rem; color: var(--muted); font-size: 0.88rem; }}
.formats-strip {{
  margin-bottom: 1.25rem; padding: 1.1rem; background: var(--panel);
  border: 1px solid var(--border); border-radius: var(--radius);
}}
.formats-export-hint {{ margin: 0.85rem 0 0; font-size: 0.72rem; color: var(--muted); }}
.formats-export-hint code {{ font-size: 0.68rem; color: #93c5fd; }}
.fmt-grid {{ display: grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: 0.65rem; }}
@media (max-width: 900px) {{ .fmt-grid {{ grid-template-columns: repeat(2, 1fr); }} }}
@media (max-width: 520px) {{ .fmt-grid {{ grid-template-columns: 1fr; }} }}
.fmt-card {{
  border-radius: 10px; padding: 0.75rem; border: 1px solid var(--border);
  background: var(--panel2); min-height: 8rem;
}}
.fmt-card-link {{
  display: block; text-decoration: none; color: inherit; cursor: pointer;
  transition: border-color 0.15s, box-shadow 0.15s;
}}
.fmt-card-link:hover {{ border-color: #22c55e; box-shadow: 0 0 0 1px rgba(34,197,94,.25); }}
.fmt-card-expand {{ padding: 0; }}
.fmt-card-expand > summary.fmt-card-sum {{
  list-style: none; cursor: pointer; padding: 0.75rem; border-radius: 10px;
}}
.fmt-card-expand > summary.fmt-card-sum::-webkit-details-marker {{ display: none; }}
.fmt-card-expand[open] > summary.fmt-card-sum {{ border-bottom: 1px solid var(--border); }}
.fmt-card-expand[open] {{ border-color: #3b82f6; }}
.fmt-expand-hint, .fmt-link-hint {{
  display: block; font-size: 0.62rem; color: #93c5fd; margin-top: 0.35rem; font-weight: 600;
}}
.fmt-full {{
  padding: 0.5rem 0.75rem 0.75rem; max-height: 22rem; overflow: auto;
}}
.fmt-full pre {{
  margin: 0; font-family: "JetBrains Mono", Consolas, monospace;
  font-size: 0.6rem; line-height: 1.4; color: #a8c5e8; white-space: pre-wrap; word-break: break-word;
}}
.fmt-head {{ font-weight: 700; font-size: 0.82rem; margin-bottom: 0.15rem; }}
.fmt-sub {{ font-size: 0.68rem; color: var(--muted); margin-bottom: 0.5rem; }}
.fmt-preview pre {{
  display: block; margin: 0; font-family: "JetBrains Mono", Consolas, monospace;
  font-size: 0.62rem; line-height: 1.45; color: #a8c5e8; white-space: pre-wrap;
  word-break: break-word; max-height: 9rem; overflow: auto;
}}
.fmt-console {{ border-top: 3px solid #64748b; }}
.fmt-junit {{ border-top: 3px solid #f59e0b; }}
.fmt-json {{ border-top: 3px solid #3b82f6; }}
.fmt-html {{ border-top: 3px solid #22c55e; }}
.t-pass {{ color: var(--c-pass); font-weight: 700; }}
.t-fail {{ color: var(--c-fail); font-weight: 700; }}
.t-dim {{ color: #64748b; }}
.quality {{
  display: flex; align-items: center; gap: 0.5rem; padding: 0.7rem 1rem;
  border-radius: var(--radius); font-weight: 600; font-size: 0.9rem;
  margin-bottom: 1rem; border: 1px solid var(--border);
}}
.quality.ok {{ background: rgba(34,197,94,.1); color: var(--c-pass); border-color: rgba(34,197,94,.3); }}
.quality.bad {{ background: rgba(239,68,68,.1); color: var(--c-fail); border-color: rgba(239,68,68,.3); }}
.quality.neutral {{ background: var(--panel2); color: var(--muted); }}
.stat-grid {{
  display: grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: 0.75rem;
  margin-bottom: 1.25rem;
}}
@media (max-width: 700px) {{ .stat-grid {{ grid-template-columns: repeat(2, 1fr); }} }}
.stat-card {{
  display: flex; align-items: center; gap: 0.85rem;
  padding: 1rem 1.1rem; border-radius: var(--radius);
  background: var(--panel); border: 1px solid var(--border);
  box-shadow: var(--shadow); transition: transform .15s;
}}
.stat-card:hover {{ transform: translateY(-2px); }}
.stat-icon {{
  width: 2.5rem; height: 2.5rem; border-radius: 10px;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}}
.stat-icon svg {{ width: 1.25rem; height: 1.25rem; }}
.sc-pass .stat-icon {{ background: rgba(34,197,94,.15); color: var(--c-pass); }}
.sc-fail .stat-icon {{ background: rgba(239,68,68,.15); color: var(--c-fail); }}
.sc-skip .stat-icon {{ background: rgba(148,163,184,.15); color: var(--c-skip); }}
.sc-time .stat-icon {{ background: rgba(59,130,246,.15); color: #60a5fa; }}
.stat-label {{ font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.07em; color: var(--muted); }}
.stat-value {{ font-size: 1.75rem; font-weight: 800; font-feature-settings: "tnum"; line-height: 1.1; }}
.sc-pass .stat-value {{ color: var(--c-pass); }}
.sc-fail .stat-value {{ color: var(--c-fail); }}
.sc-skip .stat-value {{ color: var(--c-skip); }}
.sc-time .stat-value {{ color: #60a5fa; font-size: 1.35rem; }}
.analytics {{
  display: grid; grid-template-columns: 1fr 1fr; gap: 0.85rem; margin-bottom: 1.25rem;
}}
@media (max-width: 900px) {{ .analytics {{ grid-template-columns: 1fr; }} }}
.analytics-card {{
  background: var(--panel); border: 1px solid var(--border); border-radius: var(--radius);
  padding: 1rem; box-shadow: var(--shadow);
}}
.analytics-card h3 {{ margin: 0 0 0.5rem; font-size: 0.85rem; color: #cbd5e1; text-transform: uppercase; letter-spacing: 0.05em; }}
.chart-hint {{ font-size: 0.72rem; color: var(--muted); margin: 0 0 0.5rem; }}
.chart-card {{ grid-column: span 1; }}
.donut-wrap {{ display: flex; flex-wrap: wrap; align-items: center; gap: 1.25rem; justify-content: center; }}
.donut-outer {{
  width: 140px; height: 140px; border-radius: 50%; position: relative;
  box-shadow: 0 0 24px rgba(34,197,94,.2);
}}
.donut-inner {{
  position: absolute; inset: 18px; border-radius: 50%;
  background: var(--panel); display: flex; flex-direction: column;
  align-items: center; justify-content: center; border: 1px solid var(--border);
}}
.donut-pct {{ font-size: 1.5rem; font-weight: 800; color: var(--c-pass); line-height: 1; }}
.donut-sub {{ font-size: 0.6rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.06em; }}
.pie-legend {{ flex: 1; min-width: 140px; }}
.leg-row {{ display: grid; grid-template-columns: 10px 1fr auto auto; gap: 0.4rem 0.5rem; align-items: center; font-size: 0.78rem; padding: 0.2rem 0; }}
.leg-dot {{ width: 8px; height: 8px; border-radius: 50%; }}
.leg-name {{ color: #cbd5e1; }}
.leg-pct {{ color: var(--muted); font-feature-settings: "tnum"; }}
.leg-n {{ font-weight: 700; font-feature-settings: "tnum"; }}
.timeline-svg {{ width: 100%; height: auto; display: block; }}
.fail-list {{ list-style: none; margin: 0; padding: 0; }}
.fail-item {{ padding: 0.5rem 0; border-bottom: 1px solid var(--border); }}
.fail-item:last-child {{ border-bottom: none; }}
.fail-name {{ font-weight: 600; font-size: 0.82rem; color: #e2e8f0; }}
.fail-badge {{ font-size: 0.6rem; margin-left: 0.35rem; padding: 0.1rem 0.35rem; border-radius: 4px; background: rgba(239,68,68,.2); color: var(--c-fail); }}
.fail-msg {{ font-size: 0.72rem; color: var(--muted); margin-top: 0.2rem; word-break: break-word; }}
.fail-more {{ font-size: 0.75rem; color: var(--muted); padding-top: 0.35rem; }}
.good-note {{ color: var(--c-pass); font-size: 0.85rem; }}
.dur-chart {{ display: flex; flex-direction: column; gap: 0.45rem; }}
.dur-row {{ display: grid; grid-template-columns: minmax(0,1fr) 2fr auto; gap: 0.5rem; align-items: center; font-size: 0.72rem; }}
.dur-label {{ overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #94a3b8; }}
.dur-track {{ height: 8px; background: #1e293b; border-radius: 4px; overflow: hidden; }}
.dur-fill {{ height: 100%; border-radius: 4px; }}
.dur-pass {{ background: linear-gradient(90deg, #16a34a, #22c55e); }}
.dur-fail {{ background: linear-gradient(90deg, #dc2626, #ef4444); }}
.dur-error {{ background: linear-gradient(90deg, #d97706, #f59e0b); }}
.dur-skip {{ background: #64748b; }}
.dur-timeout {{ background: linear-gradient(90deg, #7c3aed, #a855f7); }}
.dur-ms {{ color: var(--muted); font-feature-settings: "tnum"; white-space: nowrap; }}
.filter-row {{ margin: 0 0 1rem; display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center; }}
.filter-row input[type="search"] {{
  flex: 1; min-width: 200px; padding: 0.55rem 0.85rem; border-radius: 8px;
  border: 1px solid var(--border); background: var(--panel2); color: var(--text); font-size: 0.9rem;
}}
.filter-row input:focus {{ outline: 2px solid var(--accent); outline-offset: 1px; }}
.date-filters {{
  display: flex; flex-wrap: wrap; align-items: center; gap: 0.45rem 0.75rem;
  width: 100%; margin-top: 0.35rem; padding-top: 0.5rem; border-top: 1px dashed var(--border);
}}
.date-filters label {{ font-size: 0.72rem; color: var(--muted); display: inline-flex; align-items: center; gap: 0.35rem; }}
.date-filters input[type="datetime-local"] {{
  padding: 0.35rem 0.45rem; border-radius: 8px; border: 1px solid var(--border);
  background: var(--panel2); color: var(--text); font-size: 0.75rem;
}}
.date-filters input[type="datetime-local"]:focus {{ outline: 2px solid var(--accent); outline-offset: 1px; }}
.btn-date-clear {{
  padding: 0.3rem 0.6rem; border-radius: 8px; border: 1px solid var(--border);
  background: var(--panel2); color: var(--muted); font-size: 0.72rem; cursor: pointer;
}}
.btn-date-clear:hover {{ border-color: #64748b; color: var(--text); }}
.date-run-hint {{ font-size: 0.68rem; color: var(--muted); }}
td.started {{ font-size: 0.72rem; color: #94a3b8; white-space: nowrap; font-feature-settings: "tnum"; }}
th.mcp-sort-started {{ cursor: pointer; user-select: none; text-decoration: underline dotted; text-underline-offset: 2px; }}
.filter-summary {{
  width: 100%; font-size: 0.78rem; color: #93c5fd; padding: 0.35rem 0.5rem;
  background: rgba(59,130,246,.08); border-radius: 8px; border: 1px solid rgba(59,130,246,.2);
}}
.filter-summary.filtered {{ color: #fbbf24; border-color: rgba(251,191,36,.35); background: rgba(251,191,36,.08); }}
.dur-filters {{ display: flex; flex-wrap: wrap; align-items: center; gap: 0.45rem 0.75rem; }}
.dur-filters label {{ font-size: 0.72rem; color: var(--muted); display: inline-flex; align-items: center; gap: 0.35rem; }}
.dur-filters input[type="number"] {{
  width: 5.5rem; padding: 0.35rem 0.45rem; border-radius: 8px; border: 1px solid var(--border);
  background: var(--panel2); color: var(--text); font-size: 0.75rem;
}}
.btn-tool {{
  padding: 0.45rem 0.75rem; border-radius: 8px; border: 1px solid var(--border);
  background: var(--panel2); color: #cbd5e1; font-size: 0.78rem; font-weight: 600; cursor: pointer;
}}
.btn-tool:hover {{ border-color: #64748b; color: var(--text); }}
.kbd-hint {{ font-size: 0.65rem; color: var(--muted); margin-left: auto; }}
.kbd-hint kbd {{
  padding: 0.1rem 0.35rem; border-radius: 4px; border: 1px solid var(--border);
  background: var(--panel2); font-family: inherit; font-size: 0.62rem;
}}
.shortcut-toast {{
  position: fixed; bottom: 1.25rem; right: 1.25rem; max-width: 320px; padding: 0.85rem 1rem;
  background: var(--panel); border: 1px solid var(--border); border-radius: 12px;
  box-shadow: var(--shadow); font-size: 0.75rem; color: var(--text); z-index: 9999;
  display: none; line-height: 1.55;
}}
.shortcut-toast.show {{ display: block; }}
html[data-theme="light"] {{
  --bg0: #f8fafc; --bg1: #f1f5f9; --panel: #ffffff; --panel2: #f8fafc;
  --border: #cbd5e1; --text: #0f172a; --muted: #64748b;
  --glow: rgba(59,130,246,.08);
}}
html[data-theme="light"] body {{
  background: radial-gradient(ellipse 120% 80% at 50% -20%, #e0e7ff 0%, var(--bg0) 55%);
}}
html[data-theme="light"] .hero h1 {{
  background: linear-gradient(135deg, #1e293b 0%, #6366f1 50%, #059669 100%);
  -webkit-background-clip: text; background-clip: text;
}}
html[data-theme="light"] .brand-nav a,
html[data-theme="light"] footer a {{ color: #2563eb; }}
html[data-theme="light"] .fail-name,
html[data-theme="light"] td.name {{ color: #1e293b; }}
html[data-theme="light"] .dur-track {{ background: #e2e8f0; }}
html[data-theme="light"] .stat-grid.filtered .stat-value {{ opacity: 0.85; }}
.muted {{ color: var(--muted); }}
.portal {{ margin-bottom: 1.2rem; background: var(--panel); border: 1px solid var(--border); border-radius: var(--radius); padding: 1rem; }}
.portal h2 {{ margin: 0 0 0.75rem; font-size: 0.95rem; color: #e2e8f0; }}
.portal-grid {{ display: grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: 0.5rem; }}
@media (max-width: 800px) {{ .portal-grid {{ grid-template-columns: repeat(2, 1fr); }} }}
.portal-card {{ border-radius: 8px; padding: 0.65rem; border: 1px solid var(--border); background: var(--panel2); }}
.portal-label {{ font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); }}
.portal-score {{ font-size: 1.4rem; font-weight: 800; margin: 0.2rem 0; }}
.portal-sub {{ font-size: 0.72rem; color: var(--muted); }}
.portal-pass .portal-score {{ color: var(--c-pass); }}
.portal-fail .portal-score {{ color: var(--c-fail); }}
.portal-na .portal-score {{ color: var(--muted); }}
.portal-cov {{ font-size: 0.8rem; color: #94a3b8; margin: 0.75rem 0 0.25rem; }}
.portal-gaps {{ margin: 0.35rem 0 0; padding-left: 1.2rem; font-size: 0.75rem; color: #94a3b8; }}
.srv-panels {{ display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; margin-bottom: 1rem; }}
@media (max-width: 800px) {{ .srv-panels {{ grid-template-columns: 1fr; }} }}
.panel {{
  background: var(--panel); border: 1px solid var(--border); border-radius: var(--radius);
  padding: 0.75rem 1rem; font-size: 0.8rem; color: var(--muted);
}}
.panel h3 {{ margin: 0 0 0.5rem; font-size: 0.8rem; color: #cbd5e1; text-transform: uppercase; letter-spacing: 0.05em; }}
.env-list {{ margin: 0; padding-left: 1.1rem; }} .env-list code {{ font-size: 0.75rem; color: #a8c5e8; word-break: break-all; }}
.results-head {{ font-size: 1rem; margin: 0 0 0.65rem; color: #94a3b8; font-weight: 600; }}
.trace-block{{margin-top:.5rem;border:1px solid var(--border);border-radius:6px;padding:.5rem;background:var(--bg1)}}
.trace-row{{display:grid;grid-template-columns:4rem 4.5rem 1fr 3rem;gap:.35rem .5rem;align-items:start;padding:.25rem 0;border-bottom:1px solid var(--border);font-size:.78rem}}
.trace-row:last-child{{border-bottom:none}}
.trace-payload{{grid-column:1/-1;margin:.2rem 0 0;font-size:.72rem;max-height:8rem;overflow:auto;white-space:pre-wrap}}
.trace-request .trace-dir{{color:#5dade2}}
.trace-response .trace-dir{{color:#1abc7a}}
.trace-error .trace-dir{{color:#e74c3c}}
.pollution,.pollution-head{{color:#e67e22}}
.pollution-head{{font-size:.75rem;margin:.25rem 0}}
.file-block {{ margin-bottom: 0.6rem; border: 1px solid var(--border); border-radius: var(--radius); background: var(--panel); }}
.file-sum {{
  font-weight: 600; font-size: 0.88rem; padding: 0.55rem 0.8rem; cursor: pointer; list-style: none;
  display: flex; align-items: center; gap: 0.4rem; color: #cbd5e1;
}}
.file-sum::-webkit-details-marker {{ display: none; }} .file-sum::before {{ content: "▸"; color: var(--accent); font-size: 0.75rem; }}
.file-block[open] > .file-sum::before {{ content: "▾"; }}
.file-sum .n {{ font-weight: 400; color: var(--muted); font-size: 0.8rem; }}
.inner-table {{ padding: 0 0.5rem 0.6rem; overflow-x: auto; }}
table.results {{ width: 100%; border-collapse: collapse; font-size: 0.82rem; min-width: 640px; }}
table.results th {{
  text-align: left; padding: 0.5rem 0.5rem; background: var(--panel2); color: var(--muted);
  font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.04em; border-bottom: 1px solid var(--border);
}}
th.mcp-sort-dur {{ cursor: pointer; user-select: none; text-decoration: underline dotted; text-underline-offset: 2px; }}
table.results td {{ padding: 0.5rem; border-bottom: 1px solid #2a3344; vertical-align: top; }}
tr.mcp-trow:hover {{ background: rgba(59, 130, 246, 0.06); }}
td.name {{ font-weight: 500; color: #e2e8f0; }}
.tagchip {{ display: inline-block; font-size: 0.6rem; padding: 0.1rem 0.35rem; border-radius: 3px; background: #2d3f5c; color: #94c5f8; margin: 0.1rem 0.1rem 0 0; }}
.badge {{ display: inline-block; padding: 0.12rem 0.45rem; border-radius: 4px; font-size: 0.65rem; font-weight: 700; letter-spacing: 0.04em; }}
.badge.b-pass {{ background: rgba(34,197,94,.2); color: var(--c-pass); }}
.badge.b-fail {{ background: rgba(239,68,68,.2); color: var(--c-fail); }}
.badge.b-error {{ background: rgba(245,158,11,.2); color: var(--c-err); }}
.badge.b-timeout {{ background: rgba(168,85,247,.2); color: var(--c-to); }}
.badge.b-skip {{ background: rgba(148,163,184,.25); color: #b0b8bb; }}
.flaky-pill {{ font-size: 0.6rem; color: #fbbf24; font-weight: 700; margin-left: 0.3rem; }}
td.num {{ text-align: right; font-feature-settings: "tnum"; color: #94a3b8; font-size: 0.8rem; white-space: nowrap; }}
details.row-detail {{ max-width: 100%; }} details.row-detail[open] summary {{ color: #93c5fd; }}
summary.row-dsum {{ cursor: pointer; font-size: 0.75rem; color: #64748b; list-style: none; }}
summary.row-dsum::-webkit-details-marker {{ display: none; }}
td.detail pre {{ margin: 0.35rem 0 0; white-space: pre-wrap; word-break: break-word; color: #94a3b8; font-size: 0.75rem; max-height: 18rem; overflow: auto; }}
.footer-bar {{
  margin-top: 1.5rem; padding: 1rem 1.25rem; border-radius: var(--radius);
  background: linear-gradient(90deg, rgba(34,197,94,.12), rgba(59,130,246,.12));
  border: 1px solid var(--border); text-align: center;
}}
.footer-bar strong {{ color: #e2e8f0; font-size: 0.9rem; letter-spacing: 0.04em; }}
.footer-pills {{ display: flex; flex-wrap: wrap; justify-content: center; gap: 0.5rem 1rem; margin-top: 0.5rem; font-size: 0.75rem; color: var(--muted); }}
footer {{ margin-top: 0.75rem; font-size: 0.72rem; color: var(--muted); text-align: center; }}
.feat-highlights,.cov-panel,.tags-panel,.diag-panel {{
  margin-bottom: 1.25rem; padding: 1.1rem; background: var(--panel);
  border: 1px solid var(--border); border-radius: var(--radius); box-shadow: var(--shadow);
}}
.feat-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 0.55rem; }}
.feat-chip {{
  text-align: center; padding: 0.65rem 0.4rem; border-radius: 10px;
  background: var(--panel2); border: 1px solid var(--border);
}}
.feat-val {{ display: block; font-size: 1.35rem; font-weight: 800; line-height: 1.1; }}
.feat-lbl {{ display: block; font-size: 0.62rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); margin-top: 0.2rem; }}
.feat-sec .feat-val {{ color: #f87171; }} .feat-perf .feat-val {{ color: #60a5fa; }}
.feat-res .feat-val {{ color: #a78bfa; }} .feat-trace .feat-val {{ color: #2dd4bf; }}
.feat-flaky .feat-val {{ color: #fbbf24; }} .feat-schema .feat-val {{ color: #fb923c; }}
.cov-blocks {{ display: grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap: 0.75rem; }}
@media (max-width: 900px) {{ .cov-blocks {{ grid-template-columns: 1fr; }} }}
.cov-block {{ background: var(--panel2); border-radius: 10px; padding: 0.75rem; border: 1px solid var(--border); }}
.cov-head {{ display: flex; justify-content: space-between; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem; font-weight: 600; font-size: 0.85rem; }}
.cov-bar-track {{ flex: 1; height: 6px; background: #1e293b; border-radius: 3px; overflow: hidden; max-width: 100px; }}
.cov-bar-fill {{ height: 100%; background: linear-gradient(90deg, #3b82f6, #22c55e); border-radius: 3px; }}
.cov-bar-pct {{ font-size: 0.72rem; color: var(--muted); font-feature-settings: "tnum"; white-space: nowrap; }}
.cov-chips {{ display: flex; flex-wrap: wrap; gap: 0.3rem; }}
.cov-chip {{
  font-size: 0.68rem; padding: 0.15rem 0.45rem; border-radius: 999px;
  border: 1px solid var(--border); background: #0f172a;
}}
.cov-chip.cov-ok {{ border-color: rgba(34,197,94,.45); color: #86efac; }}
.cov-chip.cov-gap {{ border-color: rgba(239,68,68,.4); color: #fca5a5; }}
.cov-chip.cov-more {{ color: var(--muted); }}
.cov-gap-note {{ font-size: 0.72rem; margin: 0.45rem 0 0; color: #fca5a5; }}
.cov-ok-note {{ color: var(--c-pass) !important; }}
.cov-auth {{ font-size: 0.8rem; color: #94a3b8; margin: 0 0 0.75rem; }}
.cov-warn {{ color: #fbbf24; }}
.tags-table-wrap {{ overflow-x: auto; }}
.tags-table {{ width: 100%; border-collapse: collapse; font-size: 0.8rem; }}
.tags-table th {{ text-align: left; padding: 0.45rem; color: var(--muted); font-size: 0.65rem; text-transform: uppercase; border-bottom: 1px solid var(--border); }}
.tags-table td {{ padding: 0.45rem; border-bottom: 1px solid #1e293b; vertical-align: middle; }}
.tags-table .fail-n {{ color: #f87171; }}
.tag-bar {{ display: inline-block; width: 80px; height: 6px; background: #1e293b; border-radius: 3px; vertical-align: middle; margin-right: 0.35rem; }}
.tag-bar-fill {{ height: 100%; background: #22c55e; border-radius: 3px; }}
.tag-rate {{ font-size: 0.72rem; color: var(--muted); }}
.diag-cols {{ display: grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap: 0.75rem; }}
@media (max-width: 800px) {{ .diag-cols {{ grid-template-columns: 1fr; }} }}
.diag-col h4 {{ margin: 0 0 0.4rem; font-size: 0.78rem; color: #cbd5e1; text-transform: uppercase; letter-spacing: 0.04em; }}
.diag-list {{ margin: 0; padding-left: 1rem; font-size: 0.78rem; }}
.diag-list a {{ color: #93c5fd; text-decoration: none; }}
.diag-list a:hover {{ text-decoration: underline; }}
.filter-chips {{ display: flex; flex-wrap: wrap; gap: 0.35rem; }}
.filter-chip {{
  padding: 0.3rem 0.65rem; border-radius: 999px; font-size: 0.72rem; font-weight: 600;
  border: 1px solid var(--border); background: var(--panel2); color: var(--muted);
  cursor: pointer; user-select: none;
}}
.filter-chip.active {{ background: rgba(59,130,246,.2); border-color: #3b82f6; color: #93c5fd; }}
.filter-chip:hover {{ border-color: #64748b; }}
.platform-panel {{
  margin-bottom: 1.25rem; padding: 1.1rem; background: var(--panel);
  border: 1px solid var(--border); border-radius: var(--radius); box-shadow: var(--shadow);
}}
.platform-table {{ width: 100%; border-collapse: collapse; font-size: 0.78rem; margin-top: 0.65rem; }}
.platform-table th {{ text-align: left; padding: 0.45rem; color: var(--muted); font-size: 0.62rem; text-transform: uppercase; border-bottom: 1px solid var(--border); }}
.platform-table td {{ padding: 0.45rem; border-bottom: 1px solid #1e293b; vertical-align: top; }}
.platform-table a {{ color: #93c5fd; text-decoration: none; }}
.chaos-legend {{ display: flex; flex-wrap: wrap; gap: 0.35rem; margin: 0.5rem 0; }}
.chaos-pill {{
  font-size: 0.65rem; padding: 0.2rem 0.5rem; border-radius: 999px;
  background: rgba(168,85,247,.15); border: 1px solid rgba(168,85,247,.35); color: #d8b4fe;
}}
.chaos-faults {{ font-size: 0.72rem; color: #fbbf24; }}
.experiments-panel {{ margin: 1rem 0; }}
.exp-table {{ width: 100%; border-collapse: collapse; font-size: 0.8rem; }}
.exp-table th, .exp-table td {{ padding: 0.45rem 0.55rem; border-bottom: 1px solid var(--border); text-align: left; vertical-align: top; }}
.exp-hypo {{ color: var(--muted); max-width: 28rem; }}
.copy-cmd {{
  padding: 0.25rem 0.5rem; border-radius: 6px; border: 1px solid var(--border);
  background: var(--panel2); color: var(--text); font-size: 0.72rem; cursor: pointer;
}}
.copy-cmd:hover {{ border-color: var(--accent); }}
.conf-row {{ display: flex; flex-wrap: wrap; align-items: center; gap: 0.85rem; margin: 0.6rem 0; }}
.conf-pills {{ display: flex; flex-wrap: wrap; gap: 0.35rem; }}
.conf-pill {{
  font-size: 0.72rem; padding: 0.2rem 0.45rem; border-radius: 6px; border: 1px solid var(--border);
}}
.conf-yes {{ background: rgba(34,197,94,.15); color: #86efac; border-color: #22c55e; }}
.conf-no {{ color: var(--muted); }}
.conf-badge {{ height: 20px; }}
.conf-reasons {{ color: var(--muted); font-size: 0.78rem; margin: 0.35rem 0 0 1rem; }}
.pct-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.55rem; margin: 0.65rem 0; }}
.pct-card {{
  text-align: center; padding: 0.65rem; border-radius: 10px;
  background: var(--panel2); border: 1px solid var(--border);
}}
.pct-k {{ font-size: 0.62rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.06em; }}
.pct-v {{ font-size: 1.35rem; font-weight: 800; color: #60a5fa; }}
.pct-u {{ font-size: 0.65rem; font-weight: 400; color: var(--muted); }}
.load-note {{ font-size: 0.75rem; margin: 0.35rem 0 0.5rem; }}
.slo-hint {{ font-size: 0.68rem; color: #fca5a5; margin-top: 0.15rem; }}
.bastion-split {{ display: grid; grid-template-columns: 1fr 1fr; gap: 0.85rem; }}
@media (max-width: 900px) {{ .bastion-split {{ grid-template-columns: 1fr; }} }}
.bastion-col-card {{
  background: var(--panel2); border-radius: 12px; padding: 0.85rem; border: 1px solid var(--border);
}}
.bastion-col-card h3 {{ margin: 0 0 0.5rem; font-size: 0.82rem; color: #e2e8f0; }}
.ci-card {{ border-top: 3px solid #3b82f6; }}
.prod-card {{ border-top: 3px solid #a855f7; }}
.bastion-ver {{ font-size: 0.78rem; color: #94a3b8; margin: 0 0 0.5rem; }}
.findings-list {{ list-style: none; margin: 0; padding: 0; }}
.finding-item {{ padding: 0.45rem 0; border-bottom: 1px solid var(--border); font-size: 0.75rem; }}
.finding-rule {{ font-family: Consolas, monospace; color: #fbbf24; }}
.finding-sev {{ font-size: 0.6rem; padding: 0.1rem 0.35rem; border-radius: 4px; background: rgba(239,68,68,.2); color: #fca5a5; }}
.finding-msg {{ color: var(--muted); margin-top: 0.15rem; }}
.bastion-cta {{ font-size: 0.72rem; margin-top: 0.5rem; }}
.pair-table {{ width: 100%; font-size: 0.72rem; border-collapse: collapse; }}
.pair-table th, .pair-table td {{ padding: 0.35rem 0.25rem; border-bottom: 1px solid #1e293b; text-align: left; }}
.pair-table .bastion-col {{ color: #c4b5fd; }}
.bastion-install {{ font-size: 0.75rem; margin: 0.65rem 0 0; color: #94a3b8; }}
.bastion-install a {{ color: #93c5fd; }}
.toolkit-panel {{
  margin-bottom: 1.25rem; padding: 1.1rem; background: var(--panel);
  border: 1px solid var(--border); border-radius: var(--radius);
}}
.toolkit-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap: 0.55rem; }}
@media (max-width: 700px) {{ .toolkit-grid {{ grid-template-columns: repeat(2, 1fr); }} }}
.toolkit-card {{
  padding: 0.75rem; border-radius: 10px; background: var(--panel2); border: 1px solid var(--border);
  border-left: 3px solid #64748b;
}}
.toolkit-chaos {{ border-left-color: #a855f7; }}
.toolkit-perf {{ border-left-color: #3b82f6; }}
.toolkit-sec {{ border-left-color: #ef4444; }}
.toolkit-res {{ border-left-color: #22c55e; }}
.toolkit-reg {{ border-left-color: #f59e0b; }}
.toolkit-trace {{ border-left-color: #2dd4bf; }}
.toolkit-n {{ font-size: 1.5rem; font-weight: 800; line-height: 1; }}
.toolkit-title {{ font-size: 0.78rem; font-weight: 600; margin-top: 0.25rem; }}
.toolkit-sub {{ font-size: 0.62rem; color: var(--muted); margin-top: 0.15rem; }}
.product-brand {{
  display: flex; flex-wrap: wrap; align-items: center; gap: 0.75rem 1rem;
  margin-bottom: 1rem; padding: 0.65rem 1rem; background: var(--panel);
  border: 1px solid var(--border); border-radius: var(--radius); box-shadow: var(--shadow);
}}
.brand-link {{
  display: inline-flex; align-items: center; gap: 0.55rem; color: var(--text);
  text-decoration: none; font-weight: 700; font-size: 0.95rem;
}}
.brand-link:hover {{ color: #93c5fd; }}
.brand-logo {{ flex-shrink: 0; display: block; }}
.brand-ver {{
  font-size: 0.65rem; font-weight: 600; color: var(--muted);
  padding: 0.12rem 0.4rem; border-radius: 999px; border: 1px solid var(--border);
  background: var(--panel2);
}}
.brand-nav {{ display: flex; flex-wrap: wrap; gap: 0.65rem 1rem; font-size: 0.78rem; }}
.brand-nav a {{ color: #93c5fd; text-decoration: none; }}
.brand-nav a:hover {{ text-decoration: underline; }}
.brand-actions {{ display: flex; flex-wrap: wrap; align-items: center; gap: 0.65rem; margin-left: auto; }}
.btn-pdf {{
  padding: 0.45rem 0.85rem; border-radius: 8px; border: 1px solid #6366f1;
  background: linear-gradient(135deg, rgba(99,102,241,.25), rgba(16,185,129,.15));
  color: #e0e7ff; font-size: 0.78rem; font-weight: 700; cursor: pointer;
}}
.btn-pdf:hover {{ border-color: #818cf8; background: rgba(99,102,241,.35); }}
@media (max-width: 640px) {{ .brand-actions {{ margin-left: 0; width: 100%; }} }}
footer a {{ color: #93c5fd; text-decoration: none; }}
footer a:hover {{ text-decoration: underline; }}
{print_css}
</style>
</head>
<body>
<div class="wrap">
  {brand_html}
  <header class="hero">
    <h1>MCP Test Report</h1>
    <p class="tagline">One test run. Multiple formats. Complete visibility.</p>
    <div class="hero-meta">
      <span class="badge-top {badge_class}">{_html_escape(exit_badge)}</span>
      <span>Harness <strong>{h_ver}</strong>{proto_line}</span>
      <span>{_html_escape(run_start)} &rarr; {_html_escape(run_end)}</span>
    </div>
  </header>
  {formats_html}
  <div class="quality {gate_cls}" role="status"><span>{_html_escape(gate)}</span></div>
  {stat_cards}
  {analytics_html}
  {features_html}
  {toolkit_html}
  {chaos_html}
  {perf_html}
  {bastion_html}
  {conformance_html}
  {portal_html}
  {experiments_html}
  {coverage_html}
  {tags_html}
  {diagnostics_html}
  <div class="filter-row">
    <label for="mcp-filter" class="muted" style="font-size:0.8rem">Filter</label>
    <input type="search" id="mcp-filter" placeholder="Name, file, status, tag… (/ to focus)" autocomplete="off" />
    <div class="filter-chips" id="mcp-status-filters">
      <span class="filter-chip active" data-status="all">All</span>
      <span class="filter-chip" data-status="passed">Passed</span>
      <span class="filter-chip" data-status="failed">Failed</span>
      <span class="filter-chip" data-status="error">Error</span>
      <span class="filter-chip" data-status="skipped">Skipped</span>
      <span class="filter-chip" data-status="timeout">Timeout</span>
    </div>
    <span class="kbd-hint no-print"><kbd>/</kbd> search · <kbd>Esc</kbd> clear · <kbd>?</kbd> shortcuts</span>
    <div id="mcp-filter-summary" class="filter-summary no-print">Showing all tests</div>
    <div class="date-filters no-print" id="mcp-date-filters">
      <span class="date-run-hint">Run window: {_html_escape(run_start)} &rarr; {_html_escape(run_end)}</span>
      <label for="mcp-date-from">From <input type="datetime-local" id="mcp-date-from" aria-label="Filter from date and time"></label>
      <label for="mcp-date-to">To <input type="datetime-local" id="mcp-date-to" aria-label="Filter to date and time"></label>
      <button type="button" class="btn-date-clear" id="mcp-date-clear">Clear dates</button>
    </div>
    <div class="dur-filters no-print">
      <label for="mcp-dur-min">Min ms <input type="number" id="mcp-dur-min" min="0" step="1" placeholder="0"></label>
      <label for="mcp-dur-max">Max ms <input type="number" id="mcp-dur-max" min="0" step="1" placeholder="∞"></label>
      <button type="button" class="btn-date-clear" id="mcp-dur-clear">Clear duration</button>
    </div>
  </div>
  <div id="mcp-shortcut-toast" class="shortcut-toast no-print" role="status" aria-live="polite"></div>
  <div class="srv-panels">
    <div class="panel">
      <h3>Server &amp; protocol</h3>
      <p><strong>Protocol</strong> {proto or "—"}</p>
      <p><strong>Capabilities</strong> {cap_preview}</p>
    </div>
    <div class="panel">
      <h3>Environment</h3>
      {env_block}
    </div>
  </div>
  <h2 class="results-head">Results by file</h2>
  {body_main}
  <div class="footer-bar">
    <strong>Multiple formats. Maximum value.</strong>
    <div class="footer-pills">
      <span>Developer friendly</span><span>CI/CD ready</span>
      <span>Data driven</span><span>Insightful reports</span>
    </div>
  </div>
  <footer>Generated by <a href="{site_esc}" target="_blank" rel="noopener noreferrer">MCP Test Harness</a> v{h_ver}
    &middot; <a href="{site_esc}" target="_blank" rel="noopener noreferrer">Product site</a>
    &middot; Self-contained HTML &middot; PDF via <strong>Save as PDF</strong> or <code>mcp-test export-pdf</code>
    &middot; <code>--report-format junit|json|html</code></footer>
</div>
<script>
(function(){{
  function expandForPrint(){{
    document.querySelectorAll("details.file-block, details.row-detail").forEach(function(d){{ d.open = true; }});
  }}
  var pdfBtn=document.getElementById("mcp-export-pdf");
  if(pdfBtn) pdfBtn.addEventListener("click", function(){{ expandForPrint(); window.print(); }});
  window.addEventListener("beforeprint", expandForPrint);
  var inp=document.getElementById("mcp-filter");
  var dateFrom=document.getElementById("mcp-date-from");
  var dateTo=document.getElementById("mcp-date-to");
  var dateClear=document.getElementById("mcp-date-clear");
  var durMin=document.getElementById("mcp-dur-min");
  var durMax=document.getElementById("mcp-dur-max");
  var durClear=document.getElementById("mcp-dur-clear");
  var filterSummary=document.getElementById("mcp-filter-summary");
  var statGrid=document.getElementById("mcp-stat-grid");
  var themeBtn=document.getElementById("mcp-theme-toggle");
  var csvBtn=document.getElementById("mcp-export-csv");
  var shortcutToast=document.getElementById("mcp-shortcut-toast");
  var runStartMs={run_start_ms_js};
  var runEndMs={run_end_ms_js};
  var statusFilter="all";
  function localInputToMs(el){{
    if(!el||!el.value) return null;
    var d=new Date(el.value);
    return isNaN(d.getTime())?null:d.getTime();
  }}
  function msToLocalInput(ms){{
    if(ms==null) return "";
    var d=new Date(ms);
    if(isNaN(d.getTime())) return "";
    var pad=function(n){{ return String(n).padStart(2,"0"); }};
    return d.getFullYear()+"-"+pad(d.getMonth()+1)+"-"+pad(d.getDate())+"T"+pad(d.getHours())+":"+pad(d.getMinutes());
  }}
  function syncFileBlocks(){{
    document.querySelectorAll("details.file-block").forEach(function(block){{
      var visible=[].slice.call(block.querySelectorAll("tr.mcp-trow")).some(function(r){{
        return r.style.display!=="none";
      }});
      block.style.display=visible?"":"none";
    }});
  }}
  function updateFilterSummary(){{
    var rows=[].slice.call(document.querySelectorAll("tr.mcp-trow"));
    var total=rows.length;
    var visible=0;
    var pass=0, fail=0, err=0, skip=0, to=0;
    rows.forEach(function(r){{
      if(r.style.display==="none") return;
      visible++;
      var st=r.getAttribute("data-status")||"";
      if(st==="passed") pass++;
      else if(st==="failed") fail++;
      else if(st==="error") err++;
      else if(st==="skipped") skip++;
      else if(st==="timeout") to++;
    }});
    if(filterSummary){{
      var filtered=visible<total;
      filterSummary.classList.toggle("filtered", filtered);
      var parts=["Showing "+visible+" of "+total+" tests"];
      if(filtered) parts.push(pass+" passed", (fail+err+to)+" failed/error/timeout", skip+" skipped");
      filterSummary.textContent=parts.join(" · ");
    }}
    if(statGrid&&visible<total){{
      statGrid.classList.add("filtered");
      var elPass=document.getElementById("mcp-stat-pass");
      var elFail=document.getElementById("mcp-stat-fail");
      var elSkip=document.getElementById("mcp-stat-skip");
      if(elPass) elPass.textContent=String(pass);
      if(elFail) elFail.textContent=String(fail+err+to);
      if(elSkip) elSkip.textContent=String(skip);
    }} else if(statGrid){{
      statGrid.classList.remove("filtered");
      var elP=document.getElementById("mcp-stat-pass");
      var elF=document.getElementById("mcp-stat-fail");
      var elS=document.getElementById("mcp-stat-skip");
      if(elP) elP.textContent=statGrid.getAttribute("data-pass")||elP.textContent;
      if(elF) elF.textContent=String(
        parseInt(statGrid.getAttribute("data-fail")||"0",10)+
        parseInt(statGrid.getAttribute("data-error")||"0",10)+
        parseInt(statGrid.getAttribute("data-timeout")||"0",10)
      );
      if(elS) elS.textContent=statGrid.getAttribute("data-skip")||elS.textContent;
    }}
  }}
  function applyFilters(){{
    var q=inp?inp.value.toLowerCase().trim():"";
    var fromMs=localInputToMs(dateFrom);
    var toMs=localInputToMs(dateTo);
    var minDur=durMin&&durMin.value?parseFloat(durMin.value):null;
    var maxDur=durMax&&durMax.value?parseFloat(durMax.value):null;
    document.querySelectorAll("tr.mcp-trow").forEach(function(r){{
      var k=(r.getAttribute("data-k")||"");
      var st=r.getAttribute("data-status")||"";
      var okStatus=(statusFilter==="all")||st===statusFilter;
      var okSearch=(!q)||k.indexOf(q)>=0;
      var startedRaw=r.getAttribute("data-started-ms");
      var startedMs=startedRaw?parseInt(startedRaw,10):null;
      var okDate=true;
      if(fromMs!=null||toMs!=null){{
        if(startedMs==null||isNaN(startedMs)) okDate=false;
        else {{
          if(fromMs!=null&&startedMs<fromMs) okDate=false;
          if(toMs!=null&&startedMs>toMs) okDate=false;
        }}
      }}
      var rowMs=parseFloat(r.getAttribute("data-ms")||"0");
      var okDur=true;
      if(minDur!=null&&!isNaN(minDur)&&rowMs<minDur) okDur=false;
      if(maxDur!=null&&!isNaN(maxDur)&&rowMs>maxDur) okDur=false;
      r.style.display=(okStatus&&okSearch&&okDate&&okDur)?"table-row":"none";
    }});
    syncFileBlocks();
    updateFilterSummary();
  }}
  function clearAllFilters(){{
    if(inp) inp.value="";
    if(dateFrom) dateFrom.value="";
    if(dateTo) dateTo.value="";
    if(durMin) durMin.value="";
    if(durMax) durMax.value="";
    statusFilter="all";
    document.querySelectorAll(".filter-chip").forEach(function(c){{
      c.classList.toggle("active", c.getAttribute("data-status")==="all");
    }});
    applyFilters();
  }}
  function csvEscape(v){{ return '"'+String(v||"").replace(/"/g,'""')+'"'; }}
  function csvCellText(v){{
    return String(v||"").replace(/\\u2014/g,"").replace(/—/g,"").trim();
  }}
  function startedCsvValue(r){{
    var iso=r.getAttribute("data-started-iso");
    if(iso) return iso;
    var ms=r.getAttribute("data-started-ms");
    if(ms){{
      var d=new Date(parseInt(ms,10));
      if(!isNaN(d.getTime())) return d.toISOString();
    }}
    return "";
  }}
  function exportVisibleCsv(){{
    var rows=[].slice.call(document.querySelectorAll("tr.mcp-trow")).filter(function(r){{
      return r.style.display!=="none";
    }});
    var lines=["name,file,status,duration_ms,started,tags"];
    rows.forEach(function(r){{
      var name=r.querySelector(".name");
      var tags=r.querySelector(".tags");
      var dur=parseFloat(r.getAttribute("data-ms")||"0");
      lines.push([
        csvEscape(csvCellText(name?name.textContent.replace(/flaky/g,""):"")),
        csvEscape(csvCellText(r.getAttribute("data-file")||"")),
        csvEscape(csvCellText(r.getAttribute("data-status")||"")),
        csvEscape(isNaN(dur)?"":String(Math.round(dur*10)/10)),
        csvEscape(startedCsvValue(r)),
        csvEscape(csvCellText(tags?tags.textContent:"")),
      ].join(","));
    }});
    var blob=new Blob(["\\ufeff"+lines.join("\\n")], {{type:"text/csv;charset=utf-8"}});
    var a=document.createElement("a");
    a.href=URL.createObjectURL(blob);
    a.download="mcp-test-filtered.csv";
    a.click();
    URL.revokeObjectURL(a.href);
  }}
  function applyTheme(theme){{
    if(theme==="light") document.documentElement.setAttribute("data-theme","light");
    else document.documentElement.removeAttribute("data-theme");
    try{{ localStorage.setItem("mcp-test-report-theme", theme); }}catch(e){{}}
    if(themeBtn) themeBtn.textContent=(theme==="light")?"Dark":"Theme";
  }}
  function toggleTheme(){{
    var cur=document.documentElement.getAttribute("data-theme");
    applyTheme(cur==="light"?"dark":"light");
  }}
  function showShortcuts(){{
    if(!shortcutToast) return;
    shortcutToast.innerHTML=(
      "<strong>Keyboard shortcuts</strong><br>"+
      "<kbd>/</kbd> Focus search · <kbd>Esc</kbd> Clear filters · <kbd>t</kbd> Toggle theme · <kbd>?</kbd> This help"
    );
    shortcutToast.classList.add("show");
    setTimeout(function(){{ shortcutToast.classList.remove("show"); }}, 4500);
  }}
  if(inp) inp.addEventListener("input", applyFilters);
  if(dateFrom) dateFrom.addEventListener("change", applyFilters);
  if(dateTo) dateTo.addEventListener("change", applyFilters);
  if(durMin) durMin.addEventListener("input", applyFilters);
  if(durMax) durMax.addEventListener("input", applyFilters);
  if(dateClear) dateClear.addEventListener("click", function(){{ if(dateFrom) dateFrom.value=""; if(dateTo) dateTo.value=""; applyFilters(); }});
  if(durClear) durClear.addEventListener("click", function(){{ if(durMin) durMin.value=""; if(durMax) durMax.value=""; applyFilters(); }});
  if(csvBtn) csvBtn.addEventListener("click", exportVisibleCsv);
  if(themeBtn) themeBtn.addEventListener("click", toggleTheme);
  try{{
    var saved=localStorage.getItem("mcp-test-report-theme");
    if(saved==="light") applyTheme("light");
  }}catch(e){{}}
  if(dateFrom&&runStartMs!=null) dateFrom.min=msToLocalInput(runStartMs);
  if(dateTo&&runEndMs!=null) dateTo.max=msToLocalInput(runEndMs);
  if(dateFrom&&runEndMs!=null) dateFrom.max=msToLocalInput(runEndMs);
  if(dateTo&&runStartMs!=null) dateTo.min=msToLocalInput(runStartMs);
  document.addEventListener("keydown", function(ev){{
    var tag=(ev.target&&ev.target.tagName)||"";
    if(ev.key==="/" && tag!=="INPUT" && tag!=="TEXTAREA"){{ ev.preventDefault(); if(inp) inp.focus(); }}
    else if(ev.key==="Escape") clearAllFilters();
    else if(ev.key==="?" && tag!=="INPUT") showShortcuts();
    else if((ev.key==="t"||ev.key==="T") && tag!=="INPUT") toggleTheme();
  }});
  applyFilters();
  document.querySelectorAll(".filter-chip").forEach(function(chip){{
    chip.addEventListener("click", function(){{
      document.querySelectorAll(".filter-chip").forEach(function(c){{ c.classList.remove("active"); }});
      chip.classList.add("active");
      statusFilter=chip.getAttribute("data-status")||"all";
      applyFilters();
    }});
  }});
  document.querySelectorAll("th.mcp-sort-dur, th.mcp-sort-started").forEach(function(h){{
    h.addEventListener("click", function(){{
      var table=h.closest("table"); if(!table) return;
      var tb=table.tBodies[0]; if(!tb) return;
      var dir=parseInt(h.getAttribute("data-dir")||"1",10);
      var attr=h.classList.contains("mcp-sort-started")?"data-started-ms":"data-ms";
      var rows=[].slice.call(tb.querySelectorAll("tr.mcp-trow"));
      rows.sort(function(a,b){{
        var av=parseFloat(a.getAttribute(attr)||"0");
        var bv=parseFloat(b.getAttribute(attr)||"0");
        return dir*(av-bv);
      }});
      h.setAttribute("data-dir", String(-dir));
      rows.forEach(function(r){{ tb.appendChild(r); }});
    }});
  }});
  document.querySelectorAll("button.copy-cmd").forEach(function(btn){{
    btn.addEventListener("click", function(){{
      var cmd=btn.getAttribute("data-cmd")||"";
      if(!cmd) return;
      if(navigator.clipboard&&navigator.clipboard.writeText){{
        navigator.clipboard.writeText(cmd).then(function(){{ btn.textContent="Copied"; }});
      }}
    }});
  }});
}})();
</script>
</body>
</html>"""

    def _one_row(self, tr: CaseResult) -> str:
        text_detail = self._failure_detail_text(tr)
        trace_html = _trace_timeline_html(tr)
        want_detail = bool(text_detail.strip() or trace_html)
        if tr.status == CaseStatus.PASSED and not want_detail:
            inner = '<span class="muted">—</span>'
        else:
            open_attr = " open" if tr.status != CaseStatus.PASSED else ""
            pre = f'<pre>{_html_escape(text_detail)}</pre>' if text_detail.strip() else ""
            inner = (
                f'<details class="row-detail"{open_attr}><summary class="row-dsum">Details</summary>'
                f'{pre}{trace_html}</details>'
            )
        tags_html = (
            " ".join(f'<span class="tagchip">{_html_escape(tg)}</span>' for tg in tr.tags) or "—"
        )
        fk = " <span class=\"flaky-pill\">flaky</span>" if tr.flaky else ""
        k = _html_escape(_search_blob(tr).replace('"', ""))
        ms = f"{tr.duration_ms:.1f}"
        started_ms = _iso_epoch_ms(tr.started_at)
        started_attr = f' data-started-ms="{started_ms}"' if started_ms is not None else ""
        started_iso_attr = ""
        if tr.started_at:
            started_iso_attr = f' data-started-iso="{_html_escape(tr.started_at)}"'
        started_cell = _html_escape(_format_started_at(tr.started_at))
        file_disp = _html_escape(_display_file(tr))
        slug = _slug_id(tr.name)
        return (
            f'<tr id="test-{slug}" class="mcp-trow row-{_status_class(tr.status)}" '
            f'data-k="{k}" data-ms="{tr.duration_ms:.4f}" data-status="{tr.status.value}" '
            f'data-file="{file_disp}"{started_attr}{started_iso_attr}>'
            f'<td class="name">{_html_escape(tr.name)}{fk}</td>'
            f'<td class="tags">{tags_html}</td>'
            f'<td class="started">{started_cell}</td>'
            f'<td><span class="badge b-{_status_class(tr.status)}">{_status_label(tr.status)}</span></td>'
            f'<td class="num" data-ms="{ms}">{ms} ms</td>'
            f'<td class="detail">{inner}</td></tr>'
        )

    def _failure_detail_text(self, tr: CaseResult) -> str:
        parts: list[str] = []
        if tr.error:
            parts.append(tr.error)
        if tr.assertion_diff:
            parts.append(tr.assertion_diff)
        if tr.traceback:
            parts.append(tr.traceback)
        if tr.schema_violations:
            for v in tr.schema_violations:
                parts.append(
                    f"schema: {v.json_path} — {v.message} (expected {v.expected_type!r}, got {v.actual_value!r})"
                )
        if tr.attempt_results and len(tr.attempt_results) > 1:
            parts.append("Attempts:")
            for a in tr.attempt_results:
                e = a.error or ""
                parts.append(f"  #{a.attempt} {a.status.value} {a.duration_ms:.1f}ms {e}")
        if tr.flaky and tr.retry_count:
            parts.append(f"Flaky: passed after {tr.retry_count} retry(ies).")
        return "\n".join(parts)

    def _failure_detail(self, tr: CaseResult) -> str:
        """Plain-text detail block (legacy / tests)."""
        text = self._failure_detail_text(tr)
        return text if text else "—"


def _summarize_caps(caps: object, limit: int = 100) -> str:
    if not isinstance(caps, dict) or not caps:
        return "—"
    keys = [str(k) for k in list(caps.keys())[:8]]
    s = ", ".join(keys)
    if len(caps) > 8:
        s += f" +{len(caps) - 8} more"
    if len(s) > limit:
        return s[: limit - 1] + "…"
    return s
