# Demo video script — 4 sections

Silent product reel (~75s): [`html/assets/video/mcp-test-harness-4-section-demo.mp4`](../html/assets/video/mcp-test-harness-4-section-demo.mp4)  
Pages player: [demo-reel.html](https://vaquarkhan.github.io/mcp-test-harness/demo-reel.html)

**Framing:** deterministic CI gates (recorded-verdict / fixtures). Not a live red-team or hosted multi-tenant dashboard.

Rebuild:

```bash
python scripts/build_demo_video.py
```

## Narration (optional voice-over)

### Intro
MCP Test Harness — four CI gates for MCP servers: security scan, load, resilience, and a report dashboard your pipeline already understands.

### 1 — Security / vulnerability scan
Run the security marker pack. Suites A through D, incident fixtures, AGENTS.md Unicode scan, and audit-chain verify. Export SARIF for code scanning. Green means the encoded corpus is caught — not novel adaptive adversaries.

```bash
mcp-test -m security --sarif-output findings.sarif
mcp-test scan-agents
mcp-test audit verify chain.json
```

### 2 — Load testing
Assert latency percentiles, throughput under concurrency, and load-phase ramps. Fail the PR when p95 or RPS slips.

```python
await assert_latency(mcp, "echo", max_p95_ms=120, iterations=50)
await assert_throughput(mcp, "echo", concurrency=20, duration_s=15, min_rps=40)
await assert_load_phases(mcp, "echo", phases=[...], max_p95_ms=200)
```

### 3 — Resilience testing
Inject chaos faults — delay, 503, truncate, schema drift. Assert graceful degrade, reconnect, and load resilience: deny-codes, no-fail-open, fairness.

```python
@marker(chaos_faults=["delay", "http_503"])
async def test_survives(): ...
await assert_no_fail_open_under_load(...)
```

### 4 — Security features → CI/CD dashboard
One run produces HTML dashboard, JUnit, JSON, and SARIF. The GitHub Action posts evidence on the PR. Artifacts are files — no always-on hosted org dashboard in core.

```bash
mcp-test --report-format html --report-output report.html \
  --junit-xml junit.xml --sarif-output findings.sarif
```

Action pin: `vaquarkhan/mcp-test-harness@v5.2.0`  
Sample report: [html/reports/sample_mcp_test_report.html](../html/reports/sample_mcp_test_report.html)

### Outro
`pip install mcp-test-harness==5.2.0` → `mcp-test init` → gate every merge. Sister product for runtime: MCP-Bastion.

## Screen-record live (optional)

If you want a live terminal capture on top of this reel:

1. Play [demo-reel.html](../html/demo-reel.html) full-screen, or run the commands above against `examples/feature-demo/`.
2. Open the generated HTML report beside GitHub Actions.
3. Keep voice-over to the nature-safe lines above (CI gate, not live offense).
