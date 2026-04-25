"""HTML report generator for the MCP Test Harness.

Generates a self-contained HTML page with inline CSS and a small amount of
client-side script for filtering and sorting. No network requests.
"""

from __future__ import annotations

from collections import defaultdict
from html import escape as _html_escape

from mcp_test_harness.models import CaseResult, CaseStatus, SessionResults


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


class HTMLReporter:
    """Generate a self-contained HTML test report."""

    def generate(self, results: SessionResults) -> str:
        p, f, e, sk, t = _outcome_tally(results)
        total_cases = p + f + e + sk + t
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
                f'<th>Test</th><th>Tags</th><th>Status</th>'
                f'<th class="mcp-sort-dur" data-dir="1" title="Click to sort by duration">Duration</th>'
                f'<th>Details</th></tr></thead><tbody>{"".join(inner_rows)}</tbody></table></div></details>'
            )

        body_main = "\n".join(row_chunks) if row_chunks else "<p class=\"muted\">No test results.</p>"

        badge_class = "exit-pass" if ok and total_cases else ("exit-fail" if not ok else "exit-neu")

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="dark light">
<title>MCP Test Report</title>
<style>
:root {{
  --bg: #0f1419;
  --panel: #1a1f2e;
  --panel-2: #222838;
  --border: #2d3848;
  --text: #e8eaed;
  --muted: #8b9aad;
  --accent: #3b82f6;
  --c-pass: #1abc7a;
  --c-fail: #e74c3c;
  --c-err: #f39c12;
  --c-skip: #7f8c8d;
  --c-to: #9b59b6;
  --shadow: 0 4px 24px rgba(0,0,0,.45);
  --radius: 10px;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  font-family: "Segoe UI", system-ui, -apple-system, Roboto, Ubuntu, sans-serif;
  background: linear-gradient(165deg, #0c0f14 0%, #111827 50%, #0f1419 100%);
  color: var(--text);
  min-height: 100vh;
  line-height: 1.45;
}}
.wrap {{ max-width: 1200px; margin: 0 auto; padding: 1.5rem 1.1rem 3rem; }}
.topbar {{
  display: flex; flex-wrap: wrap; align-items: flex-start; justify-content: space-between;
  gap: 1rem; padding: 0.9rem 1.15rem; background: var(--panel);
  border: 1px solid var(--border); border-radius: var(--radius); box-shadow: var(--shadow);
  margin-bottom: 1rem;
}}
.brand h1 {{ font-size: 1.2rem; font-weight: 700; margin: 0; }}
.brand .sub {{ font-size: 0.8rem; color: var(--muted); margin-top: 0.2rem; }}
.status-strip {{ display: flex; flex-wrap: wrap; align-items: center; gap: 0.75rem 1.2rem; width: 100%; }}
.badge-top {{
  display: inline-block; padding: 0.4rem 0.9rem; border-radius: 6px; font-weight: 800; font-size: 0.9rem; letter-spacing: 0.04em;
}}
.exit-pass {{ background: rgba(26, 188, 122, 0.25); color: var(--c-pass); border: 1px solid rgba(26, 188, 122, 0.5); }}
.exit-fail {{ background: rgba(231, 76, 60, 0.2); color: #ff6b5a; border: 1px solid rgba(231, 76, 60, 0.45); }}
.exit-neu {{ background: var(--panel-2); color: var(--muted); border: 1px solid var(--border); }}
.pct-bar-wrap {{ flex: 1; min-width: 180px; max-width: 420px; }}
.pct-label {{ font-size: 0.75rem; color: var(--muted); margin-bottom: 0.25rem; }}
.pct-bar {{ height: 10px; background: #2d3848; border-radius: 5px; overflow: hidden; border: 1px solid var(--border); }}
.pct-fill {{ height: 100%; background: linear-gradient(90deg, #1abc7a, #2ecc71); width: {pass_pct:.1f}%; transition: width .3s; }}
.filter-row {{ margin: 0.5rem 0 1rem; display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center; }}
.filter-row input[type="search"] {{
  flex: 1; min-width: 200px; max-width: 100%; padding: 0.5rem 0.75rem; border-radius: 6px; border: 1px solid var(--border);
  background: var(--panel-2); color: var(--text); font-size: 0.9rem;
}}
.meta {{ text-align: right; font-size: 0.78rem; color: var(--muted); }}
.quality {{
  display: flex; align-items: center; gap: 0.5rem; padding: 0.65rem 1rem; border-radius: var(--radius);
  font-weight: 600; font-size: 0.9rem; margin-bottom: 1rem; border: 1px solid var(--border);
}}
.quality.ok {{ background: rgba(26, 188, 122, 0.12); color: var(--c-pass); border-color: rgba(26, 188, 122, 0.35); }}
.quality.bad {{ background: rgba(231, 76, 60, 0.12); color: var(--c-fail); border-color: rgba(231, 76, 60, 0.35); }}
.quality.neutral {{ background: var(--panel-2); color: var(--muted); }}
.dashboard {{ display: grid; grid-template-columns: minmax(0,1fr) 200px; gap: 1.1rem; margin-bottom: 1.2rem; }}
@media (max-width: 800px) {{ .dashboard {{ grid-template-columns: 1fr; }} }}
.metrics {{
  display: grid; grid-template-columns: repeat(5, minmax(0,1fr)); gap: 0.5rem;
}}
@media (max-width: 700px) {{ .metrics {{ grid-template-columns: repeat(2, 1fr); }} }}
.metric {{
  background: var(--panel); border: 1px solid var(--border); border-radius: var(--radius);
  padding: 0.6rem 0.7rem; min-height: 3.8rem;
}}
.metric .k {{ font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted); margin-bottom: 0.2rem; }}
.metric .v {{ font-size: 1.35rem; font-weight: 700; font-feature-settings: "tnum"; }}
.m-pass .v {{ color: var(--c-pass); }} .m-fail .v {{ color: var(--c-fail); }} .m-err .v {{ color: var(--c-err); }}
.m-skip .v {{ color: var(--c-skip); }} .m-to .v {{ color: var(--c-to); }}
.pie-box {{
  background: var(--panel); border: 1px solid var(--border); border-radius: var(--radius);
  padding: 1rem; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 0.4rem;
}}
.pie-outer {{ width: 110px; height: 110px; border-radius: 50%; background: {pie_style}; position: relative; box-shadow: inset 0 0 0 2px var(--bg); }}
.pie-inner {{
  position: absolute; top: 50%; left: 50%; transform: translate(-50%,-50%);
  width: 52px; height: 52px; background: var(--panel); border-radius: 50%;
  display: flex; align-items: center; justify-content: center; font-size: 0.7rem; color: var(--muted);
  border: 1px solid var(--border);
}}
.srv-panels {{ display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; margin-bottom: 1rem; }}
@media (max-width: 800px) {{ .srv-panels {{ grid-template-columns: 1fr; }} }}
.panel {{
  background: var(--panel); border: 1px solid var(--border); border-radius: var(--radius);
  padding: 0.75rem 1rem; font-size: 0.8rem; color: var(--muted);
}}
.panel h3 {{ margin: 0 0 0.5rem; font-size: 0.8rem; color: #cbd5e1; text-transform: uppercase; letter-spacing: 0.05em; }}
.env-list {{ margin: 0; padding-left: 1.1rem; }} .env-list code {{ font-size: 0.75rem; color: #a8c5e8; word-break: break-all; }}
.pie-legend {{ font-size: 0.7rem; color: var(--muted); text-align: center; }}
.muted {{ color: var(--muted); }}
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
  text-align: left; padding: 0.5rem 0.5rem; background: var(--panel-2); color: var(--muted);
  font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.04em; border-bottom: 1px solid var(--border);
}}
th.mcp-sort-dur {{ cursor: pointer; user-select: none; text-decoration: underline dotted; text-underline-offset: 2px; }}
table.results td {{ padding: 0.5rem; border-bottom: 1px solid #2a3344; vertical-align: top; }}
tr.mcp-trow:hover {{ background: rgba(59, 130, 246, 0.06); }}
td.name {{ font-weight: 500; color: #e2e8f0; }}
.tagchip {{ display: inline-block; font-size: 0.6rem; padding: 0.1rem 0.35rem; border-radius: 3px; background: #2d3f5c; color: #94c5f8; margin: 0.1rem 0.1rem 0 0; }}
.badge {{ display: inline-block; padding: 0.12rem 0.45rem; border-radius: 4px; font-size: 0.65rem; font-weight: 700; letter-spacing: 0.04em; }}
.badge.b-pass {{ background: rgba(26, 188, 122, 0.2); color: var(--c-pass); }} .badge.b-fail {{ background: rgba(231, 76, 60, 0.2); color: var(--c-fail); }}
.badge.b-error {{ background: rgba(243, 156, 18, 0.2); color: var(--c-err); }} .badge.b-timeout {{ background: rgba(155, 89, 182, 0.2); color: var(--c-to); }} .badge.b-skip {{ background: rgba(127, 140, 141, 0.25); color: #b0b8bb; }}
.flaky-pill {{ font-size: 0.6rem; color: #fbbf24; font-weight: 700; margin-left: 0.3rem; }}
td.num {{ text-align: right; font-feature-settings: "tnum"; color: #94a3b8; font-size: 0.8rem; white-space: nowrap; }}
details.row-detail {{ max-width: 100%; }} details.row-detail[open] summary {{ color: #93c5fd; }}
summary.row-dsum {{ cursor: pointer; font-size: 0.75rem; color: #64748b; list-style: none; }}
summary.row-dsum::-webkit-details-marker {{ display: none; }}
td.detail pre {{ margin: 0.35rem 0 0; white-space: pre-wrap; word-break: break-word; color: #94a3b8; font-size: 0.75rem; max-height: 18rem; overflow: auto; }}
footer {{ margin-top: 1.2rem; font-size: 0.72rem; color: var(--muted); text-align: center; }}
a {{ color: var(--accent); text-decoration: none; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="topbar">
    <div class="brand" style="flex:1;min-width:200px">
      <h1>MCP Test Report</h1>
      <div class="sub">MCP Test Harness &mdash; grouped by file, filterable, self-contained</div>
    </div>
    <div class="meta">
      <span class="badge-top {badge_class}">{_html_escape(exit_badge)}</span><br>
      Harness <strong>{h_ver}</strong>{proto_line}
      <br>Run: <strong>{run_start}</strong> &rarr; <strong>{run_end}</strong>
    </div>
  </div>
  <div class="status-strip" style="margin-bottom:0.6rem">
    <div class="pct-bar-wrap">
      <div class="pct-label">Pass rate {pass_pct:.1f}% &middot; {p}/{total_cases} passed</div>
      <div class="pct-bar" title="Pass rate" role="img" aria-label="Pass rate bar"><div class="pct-fill"></div></div>
    </div>
  </div>
  <div class="filter-row">
    <label for="mcp-filter" class="muted" style="font-size:0.8rem">Filter</label>
    <input type="search" id="mcp-filter" placeholder="Name, file, status, tag…" autocomplete="off" />
  </div>
  <div class="quality {"ok" if ok and total_cases else ("bad" if not ok else "neutral")}" role="status">
    <span>{_html_escape(gate)}</span>
  </div>
  <div class="dashboard">
    <div>
      <div class="metrics">
        <div class="metric m-pass"><div class="k">Passed</div><div class="v">{p}</div></div>
        <div class="metric m-fail"><div class="k">Failed</div><div class="v">{f}</div></div>
        <div class="metric m-err"><div class="k">Errors</div><div class="v">{e}</div></div>
        <div class="metric m-skip"><div class="k">Skipped</div><div class="v">{sk}</div></div>
        <div class="metric m-to"><div class="k">Timeouts</div><div class="v">{t}</div></div>
      </div>
    </div>
    <div class="pie-box">
      <div class="pie-outer" role="img" aria-label="Outcome mix"><div class="pie-inner">{total_ms}ms</div></div>
      <div class="pie-legend">Wall time (session)</div>
    </div>
  </div>
  <div class="srv-panels">
    <div class="panel">
      <h3>Server &amp; protocol</h3>
      <p><strong>Protocol</strong> {proto or "—"}</p>
      <p><strong>Capabilities (preview)</strong> {cap_preview}</p>
    </div>
    <div class="panel">
      <h3>Environment</h3>
      {env_block}
    </div>
  </div>
  <h2 style="font-size:1rem;margin:0 0 .5rem;color:var(--muted);font-weight:600;">Results by file</h2>
  {body_main}
  <footer>Self-contained report &middot; filter + column sort in each table. Open <code>metadata</code> in JSON report for machine parsing.</footer>
</div>
<script>
(function(){{
  var inp=document.getElementById("mcp-filter");
  if(inp) inp.addEventListener("input",function(){{
    var q=this.value.toLowerCase().trim();
    document.querySelectorAll("tr.mcp-trow").forEach(function(r){{
      var k=(r.getAttribute("data-k")||"");
      r.style.display=(!q||k.indexOf(q)>=0)?"table-row":"none";
    }});
  }});
  document.querySelectorAll("th.mcp-sort-dur").forEach(function(h){{
    h.addEventListener("click", function(){{
      var table=h.closest("table"); if(!table) return;
      var tb=table.tBodies[0]; if(!tb) return;
      var dir=parseInt(h.getAttribute("data-dir")||"1",10);
      var rows=[].slice.call(tb.querySelectorAll("tr.mcp-trow"));
      rows.sort(function(a,b){{ return dir*(parseFloat(a.getAttribute("data-ms")||0)-parseFloat(b.getAttribute("data-ms")||0)); }});
      h.setAttribute("data-dir", String(-dir));
      rows.forEach(function(r){{ tb.appendChild(r); }});
    }});
  }});
}})();
</script>
</body>
</html>"""

    def _one_row(self, tr: CaseResult) -> str:
        detail = self._failure_detail(tr)
        want_detail = bool(detail.strip() and detail.strip() != "—")
        if tr.status == CaseStatus.PASSED and not want_detail:
            inner = '<span class="muted">—</span>'
        else:
            open_attr = " open" if tr.status != CaseStatus.PASSED else ""
            inner = (
                f'<details class="row-detail"{open_attr}><summary class="row-dsum">Details</summary>'
                f'<pre>{_html_escape(detail)}</pre></details>'
            )
        tags_html = (
            " ".join(f'<span class="tagchip">{_html_escape(tg)}</span>' for tg in tr.tags) or "—"
        )
        fk = " <span class=\"flaky-pill\">flaky</span>" if tr.flaky else ""
        k = _html_escape(_search_blob(tr).replace('"', ""))
        ms = f"{tr.duration_ms:.1f}"
        return (
            f'<tr class="mcp-trow row-{_status_class(tr.status)}" data-k="{k}" data-ms="{tr.duration_ms:.4f}">'
            f'<td class="name">{_html_escape(tr.name)}{fk}</td>'
            f'<td class="tags">{tags_html}</td>'
            f'<td><span class="badge b-{_status_class(tr.status)}">{_status_label(tr.status)}</span></td>'
            f'<td class="num" data-ms="{ms}">{ms} ms</td>'
            f'<td class="detail">{inner}</td></tr>'
        )

    def _failure_detail(self, tr: CaseResult) -> str:
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
        return "\n".join(parts) if parts else "—"


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
