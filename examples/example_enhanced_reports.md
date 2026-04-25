# Enhanced reports (HTML + JSON + JUnit)

This project now includes richer report output beyond basic pass/fail counts.

## HTML report highlights

- Top status badge (`RUN PASSED` / `RUN FAILED`)
- Pass-rate progress bar
- Grouping by file/module (collapsible sections)
- Tag chips and flaky indicator
- Filter box (name/file/status/tag)
- Sort by duration
- Expandable details (errors, diffs, traceback, retries, schema violations)
- Environment and protocol panels

Generate:

```bash
mcp-test --report-format html --report-output reports/mcp-results.html
```

Open sample:

- [`feature-demo/reports/sample_mcp_test_report.html`](feature-demo/reports/sample_mcp_test_report.html)

## JSON report highlights

- Metadata: harness version, protocol version, started/finished timestamps
- Environment block (python/platform/cwd/server command/transport)
- Suite percentiles: p50/p95/p99
- Per-test fields: `file`, `tags`, `started_at`, retry history, schema violations, flaky flag

Generate:

```bash
mcp-test --report-format json --report-output reports/mcp-results.json
```

## JUnit report highlights

- Normalized `classname` paths (`/` separators)
- `testsuite` timestamp + hostname
- Suite-level properties (harness/protocol/server context)
- Optional per-test tag properties

Generate:

```bash
mcp-test --report-format junit --report-output reports/mcp-results.xml
```

## Recommended CI setup

Run tests + generate JUnit for CI integrations, and keep HTML/JSON as artifacts for debugging.

