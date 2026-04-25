# Enterprise and governance notes

This page captures governance-focused capabilities often requested by larger teams.

> **Important:** this document is operational guidance, not legal advice. Regulatory applicability depends on your system, use case, and jurisdiction.

## Common requirements

- immutable/signed test run evidence
- role/tenant access matrix validation
- policy-as-code checks in CI
- supply-chain traceability context (runtime + dependency metadata)

## Recommended implementation posture

1. Keep core harness outputs structured and reproducible.
2. Add governance-heavy features through optional integrations/plugins.
3. Use CI artifacts as source evidence; publish externally only when required.

## Candidate roadmap items

- audit log export format
- role/tenant scenario helpers
- policy engine adapter hooks
- compliance-oriented report packaging

## How this helps with the EU AI Act (practical mapping)

For teams building AI-enabled products in the EU (or selling into the EU), MCP Test Harness can support evidence-generation and technical control validation.

### Useful support areas

- **Repeatable verification in CI**
  - deterministic tests, schema validation, snapshot regressions, and latency budgets provide repeatable verification outputs.
- **Technical documentation inputs**
  - JSON/JUnit/HTML reports and CI artifacts can be referenced as evidence of test execution and change controls.
- **Risk and robustness checks**
  - negative-path assertions, protocol checks, and optional security suites help show robustness testing practices.
- **Operational traceability**
  - structured outputs plus build metadata help create auditable trails (when combined with your CI retention policies).

### Typical control/evidence workflow

1. Define requirement-linked test suites (functional, security, performance).
2. Gate merges on test outcomes in CI.
3. Retain machine-readable reports (`json`, `junit`) as audit artifacts.
4. Link artifacts to release records and change logs.
5. Periodically review coverage gaps (for example, advertised tools not yet tested).

### EU AI Act starter demo (in this repo)

For a runnable starting point, see:

- `examples/feature-demo/eu-ai-act/test_eu_ai_act_demo.py`
- `examples/feature-demo/eu-ai-act/mcp_test_eu_ai_act_demo.yaml`

This demo focuses on authorization boundaries, deterministic behavior checks, and auditable report output patterns that teams commonly map into EU AI Act technical evidence workflows.

### Where you still need additional controls

MCP Test Harness does **not** replace:

- legal classification of AI risk tiers
- organizational governance, human oversight policy, incident response policy
- runtime monitoring obligations by itself
- documentation obligations not tied to software tests

Use this harness as one layer in a broader compliance program.

## Other common regulatory/compliance contexts

The same test evidence approach is also useful for:

- **SOC 2 / ISO 27001** change management and control testing evidence
- **NIS2 / internal secure SDLC** technical verification steps
- **sector-specific assurance** where reproducible test artifacts are required

In all cases, keep policy mapping in your GRC system and use harness outputs as supporting technical evidence.

