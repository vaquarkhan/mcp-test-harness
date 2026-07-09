# RFC-005: Resiliency experiment catalog (AWS FIS style)

## Status

Accepted (v1)

## Summary

Ship a curated library of ready-to-run resiliency experiments with guardrails and a
scorecard. Each experiment is a thin declarative template that compiles to existing
`chaos.py` faults and `resiliency.py` assertions. Users run:

```bash
mcp-test experiment list
mcp-test experiment run crash-mid-call
mcp-test experiment run --suite core
mcp-test experiment scorecard --report results.json
```

## Motivation

The harness already injects protocol-aware faults and checks recovery. What is
missing is **packaging**: named templates, targets, stop conditions, and a
resiliency grade suitable for CI gates and demos. This powers the **Resilient**
conformance level (RFC-002).

## Non-goals

- Hosted SaaS console or remote fault injection from our infrastructure.
- A second primary test DSL. Python tests under `tests/` remain the source of truth.
- Replacing k6/JMeter for datacenter-scale load.

## Design

### Catalog

Bundled YAML at `src/mcp_test_harness/experiments/catalog.yaml` defines:

- **suites** (`core`, `full`): named experiment groups.
- **experiments**: id, title, hypothesis, fault, assertion, target, stop_condition,
  status (`ready` | `planned`).

`planned` experiments appear in `experiment list` but compile to skipped cases until
fault types exist.

### Compiler

`experiments/compiler.py` maps each template to a synthetic `HarnessCase`:

- Tags: `experiment`, `resiliency`, `experiment:<id>`.
- Chaos faults from template flow into `@marker(chaos_faults=[...])` semantics.
- Assertion kind selects the async test body (reuses `resiliency.py` / `assertions.py`).

### Stop conditions

Each template may declare `stop_condition.abort_if` triggers:

| Trigger | Meaning |
|---------|---------|
| `unhandled_exception` | Case ended with `error` status |
| `secret_leak` | Error/traceback matches secret scanner patterns |
| `hang` | Case timed out |
| `server_crash` | Server process exited during the case |

When a stop condition fires, the experiment is marked **aborted** in the scorecard
even if the underlying assertion might have passed.

### Scorecard

`experiments/scorecard.py` builds:

```json
{
  "grade": "B",
  "score_pct": 85.7,
  "passed": 6,
  "failed": 1,
  "skipped": 0,
  "aborted": 0,
  "experiments": [
    {
      "id": "latency-injection",
      "title": "Latency injection",
      "hypothesis": "...",
      "status": "passed",
      "aborted": false
    }
  ]
}
```

Merged into `SessionResults.unified_summary["experiments"]` for JSON/HTML reports.

### CLI

Subcommand `mcp-test experiment` with `list`, `run`, and `scorecard`. `run` accepts
the same server/config flags as the main harness.

### Reporting

HTML report gains a **Resiliency experiments** panel when experiment results are
present: hypothesis, pass/fail, grade, and copy-command for each experiment.

### v1 catalog

| Id | Status | Maps to |
|----|--------|---------|
| `latency-injection` | ready | chaos delay + tool call |
| `partial-response` | ready | chaos truncate |
| `graceful-degradation` | ready | `assert_degrades_gracefully` |
| `reconnect-storm` | ready | `assert_reconnects` |
| `crash-mid-call` | ready | `assert_survives_crash` (session error burst; not process kill) |
| `gateway-503` | ready | chaos 503 |
| `schema-drift-handling` | ready | chaos schema_drift |
| `malformed-jsonrpc-flood` | planned | transport fault (future) |
| `oversized-context` | planned | payload fault (future) |
| `tool-hang` | planned | stall mid-response (future) |
| `slow-loris` | planned | stall mid-stream (future) |
| `concurrent-overload` | planned | scheduler throughput (future) |
| `out-of-order-ids` | planned | transport fault (future) |
| `capability-drift` | planned | session capability change (future) |

## Conformance link

RFC-002 **Resilient** level: pass the `core` suite with score >= 80% and zero
aborted guardrail violations.

## Future work

- Process-level `crash-mid-call` via `lifecycle.py` supervision.
- Transport-level faults in `chaos.py` for JSON-RPC envelope attacks.
- Optional `mcp-test serve` local read-only UI to browse catalog and launch runs.
