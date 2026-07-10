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
| Conformance levels + badge (RFC-002) | **Shipped** | Boot / Protocol / Covered / Secure / Resilient |
| `mcp-test try` | **Shipped** | Zero-config probe; optional `--suite core` |
| `mcp-test conformance grade\|badge` | **Shipped** | Report grading + README snippet |
| GitHub Marketplace Action + level in PR | **Shipped** | [Marketplace listing](https://github.com/marketplace/actions/mcp-test-harness); pin `@v3.0.0`+ |
| Record to suite (RFC-001) | **Shipped** | `mcp-test record` → tests + snapshots |
| pre-commit hook | **Shipped** | `.pre-commit-hooks.yaml` + [examples/pre-commit-config.yaml](../examples/pre-commit-config.yaml) |

## Tier 2–5 (summary)

Protocol depth (full revisioned suite, transport matrix, contract replay), security corpus feed (RFC-003), DX (trends, flakiness quarantine), enterprise (signed audits, OPA). See earlier backlog discussion.

## Next release theme

> **Adoption complete (Tier 1).** Record-to-suite + pre-commit ship in **3.0.0**. Next: public badge wall / transport matrix.
