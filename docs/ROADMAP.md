# Product roadmap (near-term)

This roadmap groups planned capabilities into practical delivery phases while preserving the core identity of this project:

- **MCP-aware**
- **CI-first**
- **deterministic by default**

## Now (high ROI, low risk)

1. `mcp-test doctor` onboarding and health diagnostics (implemented).
2. HTML report UX polish (grouping, filter, sort, status badges, run metadata).
3. Performance strategy docs and explicit product positioning.
4. Example/demo expansion for feature coverage and discoverability.

## Next (major value unlock)

1. Security baseline assertions:
   - prompt injection payload checks
   - traversal/injection payload checks
   - secret leak scanner
2. MCP trace capture per test and timeline rendering in HTML.
3. Tool/resource coverage map ("advertised but not tested").
4. Throughput + baseline-based performance regression gates.

## Later (platform and enterprise)

1. Contract recording/replay and compatibility matrix runs.
2. GitHub Checks/reporter ecosystem integrations.
3. Governance features:
   - signed audit exports
   - role/tenant matrices
   - policy-as-code plugin adapters

## Scope guardrails

Core harness should own:

- protocol-aware assertions and CI gates
- reproducible local/CI reports

Core harness should not replace:

- distributed load generators
- full observability backends
- org-specific policy engines

Those remain integrations/plugins.

