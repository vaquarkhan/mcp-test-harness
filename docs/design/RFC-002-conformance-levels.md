# RFC-002: Conformance levels and badge

## Status

Accepted (v1)

## Summary

Define named conformance levels for MCP servers and emit a badge plus machine-readable
scorecard from harness runs. A zero-config entry point grades a server in one command:

```bash
mcp-test try --server-command "uvx awslabs.roda-mcp-server@latest"
mcp-test conformance --report results.json
```

## Motivation

A seal that README authors can paste is the strongest adoption loop. Every badge
recruits the next author. Levels also give CI and PR comments a clear gate story
beyond raw pass/fail.

Public MCP servers such as the [RODA MCP server on AWS](https://aws.amazon.com/blogs/opensource/introducing-mcp-server-for-registry-of-open-data-on-aws/)
are natural showcase targets: same install path (`uvx`), high visibility, and a
catalog-shaped tool surface that benefits from discovery + coverage grading.

## Levels (v1)

Levels are cumulative. You earn higher levels only if lower gates pass.

| Level | Name | Gate (all required) |
|-------|------|---------------------|
| 0 | **Boot** | Server starts; initialize + `tools/list` succeed |
| 1 | **Protocol** | Schema validation post-connect passes (when enabled) |
| 2 | **Covered** | Overall test gate pass **and** at least one tool tested (coverage) |
| 3 | **Secure** | Level 2 **and** security category status is `pass` (or no security tests yet → not granted) |
| 4 | **Resilient** | Level 2 **and** experiment scorecard grade A/B with score >= 80% and zero aborted (RFC-005) |

If a category was not exercised, Secure and Resilient are **not** auto-granted.
`try` without a user suite awards at most **Protocol** (Level 1) after doctor + schema.

## Scorecard shape

Attached to `unified_summary["conformance"]`:

```json
{
  "level": 2,
  "name": "Covered",
  "levels": {
    "boot": true,
    "protocol": true,
    "covered": true,
    "secure": false,
    "resilient": false
  },
  "reasons": ["security: no pass status yet"],
  "badge": {
    "label": "mcp-test",
    "message": "Covered",
    "color": "green"
  }
}
```

## CLI

- `mcp-test try --server-command "..."` — zero-config: run doctor-equivalent
  handshake + schema checks, optionally `--suite core` experiments, emit
  conformance scorecard and optional JSON/HTML report.
- `mcp-test conformance --report results.json` — grade an existing JSON report.
- `mcp-test conformance badge --level Covered` — print markdown badge snippet
  (static shields.io style for README paste).

## Reporting

- JSON: `unified_summary.conformance`
- HTML: conformance card next to the unified portal
- PR summary: bold level line + badge message

## Non-goals

- Claiming to replace an official Anthropic/spec reference conformance suite
- Hosting a badge CDN; v1 uses shields.io query URLs and local scorecard
- Auto-running third-party servers in our CI

## Showcase note (RODA)

Recommended dogfood command for the AWS RODA MCP server:

```bash
mcp-test try --server-command "uvx awslabs.roda-mcp-server@latest"
```

Document this as a community showcase, not a partnership claim.

## Future work (still Tier 1 / 2)

- GitHub Marketplace Action packaging with conformance level in PR comment
- Record to suite (RFC-001)
- Full versioned protocol conformance corpus across MCP revisions
- Signed badge / verification endpoint (optional later)
