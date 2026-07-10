# Growth roadmap (adoption engine)

Strategic order for maximum download leverage. Complements [ROADMAP.md](ROADMAP.md).

## Why public MCP servers matter

New catalog/discovery MCP servers (for example the [AWS RODA MCP server](https://aws.amazon.com/blogs/opensource/introducing-mcp-server-for-registry-of-open-data-on-aws/)) are high-visibility install targets. A one-liner that grades them:

```bash
mcp-test try --server-command "uvx awslabs.roda-mcp-server@latest"
```

turns “cool new MCP” blog posts into “paste this badge” moments. That is Tier 1.

## Tier 1: adoption engine

| Item | Status | Notes |
|------|--------|-------|
| Conformance levels + badge (RFC-002) | **Shipped (code)** | Boot / Protocol / Covered / Secure / Resilient |
| `mcp-test try` | **Shipped (code)** | Zero-config probe; optional `--suite core` |
| `mcp-test conformance grade\|badge` | **Shipped (code)** | Report grading + README snippet |
| GitHub Marketplace Action + level in PR | **Shipped (code)** | Root `action.yml` + outputs / PR comment; list on Marketplace after `v2.2.0` |
| Record to suite (RFC-001) | Pending | Kill write-the-tests barrier |
| pre-commit hook | Pending | Fast Level 0/1 before push |

## Tier 2–5 (summary)

Protocol depth (full revisioned suite, transport matrix, contract replay), security corpus feed (RFC-003), DX (trends, flakiness quarantine), enterprise (signed audits, OPA). See earlier backlog discussion; do **not** block downloads on these before Marketplace + badge are live.

## Next release theme

> **Conformance.** Badge + `try` + Action conformance outputs ship in **2.2.0**; complete GitHub Marketplace listing from the release UI after the tag.
