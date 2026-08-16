# Demo video script — 4 sections (real product pages)

Silent product reel (~60s): [`html/assets/video/mcp-test-harness-4-section-demo.mp4`](../html/assets/video/mcp-test-harness-4-section-demo.mp4)  
Pages player: [demo-reel.html](https://vaquarkhan.github.io/mcp-test-harness/demo-reel.html)

**How it is built:** Playwright drives Chromium against a local server of `html/` and records
scrolling the real docs/report pages. Title cards are still generated; page footage is not stock art.

```bash
python scripts/build_demo_video.py
```

Requires: `ffmpeg`, `Pillow`, `playwright` + Chromium (`python -m playwright install chromium`).

**Framing:** deterministic CI gates (recorded-verdict / fixtures). Not a live red-team or hosted multi-tenant dashboard.

## Pages captured

| Section | Real pages |
|---------|------------|
| 1 Security scan | `guide/security.html`, `examples.html` |
| 2 Load testing | `guide/performance.html` |
| 3 Resilience | `guide/resiliency.html`, `guide/chaos.html` |
| 4 CI/CD dashboard | `reports/sample_mcp_test_report.html`, home `#demo-video`, `integrations.html` |

## Narration (optional voice-over)

### Intro
MCP Test Harness — four CI gates, shown on the real product site.

### 1 — Security / vulnerability scan
Security guide: Suites A–D, audit verify, scan-agents. Examples assertion table.

```bash
mcp-test -m security --sarif-output findings.sarif
mcp-test scan-agents
mcp-test audit verify chain.json
```

### 2 — Load testing
Performance guide: latency percentiles, throughput, load-phase ramps.

### 3 — Resilience testing
Resiliency and chaos docs: fault injection, degrade, reconnect, no-fail-open.

### 4 — Security → CI/CD dashboard
Sample HTML report dashboard, then Integrations / Action distribution.

```bash
mcp-test --report-format html --report-output report.html \
  --junit-xml junit.xml --sarif-output findings.sarif
```

### Outro
`pip install mcp-test-harness==5.2.0` → `mcp-test init` → gate every merge.
