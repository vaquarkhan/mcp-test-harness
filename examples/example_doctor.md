# `mcp-test doctor` (server health check, no tests required)

Use `doctor` when you want a fast answer to:

- does the server start?
- does MCP initialize succeed?
- what protocol version/capabilities are exposed?
- can we list tools/resources/prompts?
- do post-connect schema checks pass?

## Basic usage

```bash
# uses mcp-test.yaml if present in cwd
mcp-test doctor
```

## Override startup details

```bash
mcp-test doctor --server-command "python -m your_package.mcp" --transport stdio
```

## Skip schema checks (quick triage mode)

```bash
mcp-test doctor --no-schema
```

## Typical workflow

1. Run `mcp-test doctor` first when onboarding a server.
2. Fix startup/handshake/schema issues until doctor is green.
3. Then run full tests with `mcp-test`.

## Why this matters

`doctor` is designed for **zero-test diagnostics**. It saves time when failures are caused by startup, handshake, or protocol-shape issues rather than test logic.

