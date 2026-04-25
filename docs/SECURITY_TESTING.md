# Security testing strategy

This page defines how MCP Test Harness approaches security testing without turning the core into a full runtime WAF.

## Goal

Catch high-value security regressions in CI using MCP-aware tests:

- prompt injection behavior
- unsafe input handling (SQL/command/path payloads)
- auth/RBAC expectation checks
- output leak checks (secrets/PII)

## Recommended baseline pack

1. **Prompt injection checks** against known payload libraries.
2. **Input abuse checks** for tool args likely to contain commands, SQL, or paths.
3. **Path traversal checks** for resource/file-style arguments.
4. **Auth/RBAC checks** for protected tool calls.
5. **Output leak scanner** for API keys/tokens/JWT/SSH key patterns.

## New auth boundary assertions

The harness now includes security-oriented assertion helpers for authorization tests:

- `assert_tool_denied(...)` - verifies a protected call is rejected.
- `assert_authorization_boundary(...)` - verifies the same operation is allowed for one context and denied for another.

These helpers are designed for per-operation checks that reduce "confused deputy" risk in MCP integrations.

## Integration model

- Keep core assertions deterministic and cheap.
- Optional heavy scanners (for example Presidio-based PII checks) should be plugin/extra-driven.
- Runtime protection remains a companion concern (for example [MCP-Bastion](https://github.com/vaquarkhan/MCP-Bastion)).

## CI usage guidance

- Run a fast security smoke subset on every PR.
- Run full payload suites on main/nightly.
- Treat security assertions as merge gates for protected surfaces.

## Compliance note (EU AI Act and similar frameworks)

Security test artifacts from this harness can support compliance evidence packages (for example, demonstrating technical robustness checks and secure change controls). They should be used alongside governance, risk, and legal review processes; test results alone are not a full compliance determination.

