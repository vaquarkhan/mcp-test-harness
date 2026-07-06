# Performance testing with MCP Test Harness

You can run **automation (functional) tests** and **performance / latency** checks in the **same** `test_*.py` files. The harness does not use a second framework — it extends the same async tests with a latency assertion and optional **marker** filtering.

## Why this matters for MCP

MCP performance testing should be protocol-aware. Generic load tools usually do not handle MCP-specific concerns by default (initialize/session flow, MCP response shape validation, and tool-oriented assertions in the same run). In practice, correctness and latency are coupled for agents: a correct answer that arrives too late can still fail the workflow.

For product framing and roadmap, see [PERFORMANCE_TESTING_STRATEGY.md](PERFORMANCE_TESTING_STRATEGY.md).

## 1. Single-call budget (regression: “this call must stay fast”)

```python
from mcp_test_harness import assert_latency, marker

@marker(tags=["perf"])
async def test_search_stays_under_500ms(mcp_server):
    await assert_latency(
        mcp_server,
        "search",
        {"q": "hello"},
        max_ms=500.0,
    )
```

`assert_latency` times one `call_tool` and fails if it exceeds `max_ms` (milliseconds).

## 2. Warmup + many samples (JIT / p95 SLOs)

For noisy or cold-start systems, use **warmup** (untimed) and **multiple runs** with an **aggregate**:

| `aggregate` | Use when you care about |
|-------------|-------------------------|
| `max` (default) | Worst of N runs (strict) |
| `p95` / `p99` | Common SLO style on repeated samples |
| `mean` / `median` | Average / typical latency |

```python
@marker(tags=["perf", "slow"])
async def test_index_tool_p95(mcp_server):
    await assert_latency(
        mcp_server,
        "build_index",
        {"path": "/tmp"},
        max_ms=2000.0,
        warmup=2,
        runs=20,
        aggregate="p95",
    )
```

## 3. Run only performance tests in CI (optional)

Tag perf tests, then use the harness **marker** filter (same as a tag name):

```bash
mcp-test -m perf --server-command "python my_server.py" tests/
```

Run everything **except** a tag by discovering all tests and using two jobs, or split files (`tests/perf_*.py`) and point `mcp-test` at the right path. The CLI matches any tag listed in `markers["tags"]` for `-m` (see [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) markers section).

## 4. Concurrent load (`assert_throughput`)

Gate **minimum RPS**, **p99 latency under load**, and **error rate** in one burst:

```python
@marker(tags=["perf"])
async def test_reserve_under_load(mcp_server):
    await assert_throughput(
        mcp_server,
        "reserve",
        {"sku": "A1"},
        concurrent=8,
        total_calls=32,
        min_rps=10.0,
        max_p99_ms=500.0,
        max_error_rate=0.02,
        warmup=2,
    )
```

| Parameter | Meaning |
|-----------|---------|
| `min_rps` | Fail if sustained requests/sec is below this |
| `max_p99_ms` | Fail if p99 per-call latency (ms) in the burst exceeds this |
| `max_error_rate` | Fail if fraction of exceptions or `isError` responses exceeds this (0.0–1.0) |

## 5. Performance baselines

Capture baselines in JSON and fail on drift:

```python
from mcp_test_harness import assert_latency_within_baseline, save_baseline

# Once: save_baseline("perf-baseline.json", {"search_p99": 450.0})
await assert_latency_within_baseline(
    mcp_server, "search", {"q": "x"},
    "perf-baseline.json", "search_p99",
    max_regression_pct=15.0,
)
```

## 6. Relationship to `assert_tool_idempotent`

- **`assert_tool_idempotent`** checks **correctness** (same output across calls).
- **`assert_latency`** checks **time** (under a budget, optionally with p95/mean).

You can use both in one test if the tool is idempotent and you want speed + stability.

## 7. What this is not

- **Not** a datacenter-scale load generator — use k6/JMeter for cluster RPS; harness owns **MCP-aware SLO gates** on a test server process.
- **Not** a substitute for **production** APM; this is for **CI** and **regression**.

For **Postman-style multi-step “collection”** scenarios (chaining tool calls, environment-like config, roadmap for a declarative format), see [COLLECTIONS.md](COLLECTIONS.md).

For runtime protection (rate limits, cost caps) in **production**, see [MCP-Bastion](https://github.com/vaquarkhan/MCP-Bastion).
