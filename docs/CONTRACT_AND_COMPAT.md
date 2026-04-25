# Contract and compatibility testing

This page describes compatibility-oriented testing goals for MCP servers using the harness.

## Contract testing

Target outcome:

- capture representative tool/resource/prompt traces
- replay those traces as CI tests
- fail on behavior drift

This model protects downstream agent/workflow consumers from accidental changes.

## Compatibility matrix testing

Target outcome:

- run the same behavior checks across protocol versions and client stacks
- report pass/fail matrix by version/client

Use cases:

- upgrade confidence
- cross-SDK serialization checks
- staged rollout validation

## Relationship to conformance

- **Conformance** asks: does implementation match the spec?
- **Contract tests** ask: does implementation still satisfy consumer expectations?

Both are useful and complementary.

