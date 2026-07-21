# Example: Stateless SEP-2575 conformance (`mcp-test conformance stateless`)

> [!TIP]
> **Feature highlight:** adversarial certification for MCP **2026-07-28** Streamable HTTP (no `initialize` handshake). Design: [RFC-006](../docs/design/RFC-006-stateless-mcp.md). Full walkthrough: [TUTORIAL_STATELESS.md](../docs/TUTORIAL_STATELESS.md).

## Command

```bash
mcp-test conformance stateless \
  --url http://localhost:8080/mcp \
  --protocol-version 2026-07-28 \
  --generate-badge \
  --verbose
```

## Expected output (success)

```
mcp-test conformance stateless — SEP-2575 / SEP-2243
  URL: http://localhost:8080/mcp
  Protocol: 2026-07-28

  [PASS] Baseline Discover: ...
  [PASS] Missing Protocol Header: Expected HTTP 400, got 400
  ...
SERVER CERTIFIED: 100% stateless conformance (SEP-2575 / SEP-2243)

README badge:
  ![MCP Stateless Compliant](https://img.shields.io/badge/MCP_Stateless-Compliant-brightgreen?style=for-the-badge)
```

Exit **0** on full pass; **1** if any check fails.

## Versus stateful conformance

| Command | Mode |
|---------|------|
| `mcp-test try --server-command "…"` | Stateful Boot→Protocol (RFC-002) |
| `mcp-test conformance grade --report report.json` | Grade a suite JSON report |
| `mcp-test conformance stateless --url …` | SEP-2575 HTTP adversarial matrix |

Stateful paths are **unchanged**. Use both when you ship stdio *and* cloud HTTP endpoints.
