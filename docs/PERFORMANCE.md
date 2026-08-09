# Performance testing with MCP Test Harness

You can run **automation (functional) tests** and **performance / latency** checks in the **same** `test_*.py` files. The harness does not use a second framework — it extends the same async tests with latency and load assertions and optional **marker** filtering.

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

## 2. Warmup + many samples (JIT / percentile SLOs)

For noisy or cold-start systems, use **warmup** (untimed) and **multiple runs** with an **aggregate**:

| `aggregate` | Use when you care about |
|-------------|-------------------------|
| `max` (default) | Worst of N runs (strict) |
| `p90` / `p95` / `p99` | Common SLO style on repeated samples |
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

Gate **minimum RPS**, **percentile latency under load**, and **error rate** in one burst. Prefer **`duration_s`** for a closed-loop soak at fixed concurrency; use **`total_calls`** for a fixed-size burst.

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
        max_p95_ms=400.0,
        max_p99_ms=500.0,
        max_error_rate=0.02,
        warmup=2,
    )
```

Closed-loop soak (workers keep calling until the window ends):

```python
@marker(tags=["perf"])
async def test_reserve_soak(mcp_server):
    await assert_throughput(
        mcp_server,
        "reserve",
        {"sku": "A1"},
        concurrent=16,
        duration_s=5.0,
        min_rps=20.0,
        max_p90_ms=300.0,
        max_p95_ms=450.0,
        max_error_rate=0.01,
    )
```

Weighted multi-tool mix (models a realistic traffic blend):

```python
@marker(tags=["perf"])
async def test_mixed_tool_load(mcp_server):
    await assert_throughput(
        mcp_server,
        calls=[
            {"tool": "echo", "arguments": {"text": "ping"}, "weight": 1},
            {"tool": "search", "arguments": {"q": "x"}, "weight": 3},
        ],
        concurrent=8,
        duration_s=3.0,
        min_rps=15.0,
        max_p95_ms=500.0,
    )
```

| Parameter | Meaning |
|-----------|---------|
| `concurrent` | Max in-flight `call_tool` calls (semaphore size) |
| `total_calls` | Fixed burst size (ignored when `duration_s` is set; default `16`) |
| `duration_s` | Closed-loop window in seconds at the given concurrency |
| `min_rps` | Fail if sustained requests/sec is below this |
| `max_p90_ms` / `max_p95_ms` / `max_p99_ms` | Fail if the matching per-call latency percentile exceeds the budget |
| `max_error_rate` | Fail if fraction of exceptions or `isError` responses exceeds this (0.0–1.0) |
| `warmup` | Untimed calls before the measured window |
| `calls` | Optional weighted mix of `{tool, arguments, weight}` (replaces single `tool_name` / `arguments`) |

### 4.1 Concurrency ramp (`assert_load_phases`)

Run ordered phases (warmup → ramp) and apply SLO gates only to the **aggregate of non-warmup** phases:

```python
from mcp_test_harness import assert_load_phases, marker

@marker(tags=["perf"])
async def test_reserve_ramp(mcp_server):
    await assert_load_phases(
        mcp_server,
        "reserve",
        {"sku": "A1"},
        phases=[
            {"name": "warmup", "concurrent": 4, "duration_s": 1, "warmup": True},
            {"name": "c8", "concurrent": 8, "duration_s": 2},
            {"name": "c32", "concurrency": 32, "duration_s": 2},
        ],
        min_rps=10.0,
        max_p95_ms=600.0,
        max_error_rate=0.02,
    )
```

Each phase accepts `name`, `concurrent` / `concurrency`, `duration_s` and/or `total_calls` / `requests`, and `warmup` (bool). Warmup phases are measured for visibility but **excluded** from the aggregate gates.

### 4.2 Stateless Streamable HTTP (`assert_stateless_throughput`)

For **MCP 2026-07-28** stateless servers (no `initialize` handshake, no `Mcp-Session-Id`), load-test the raw HTTP endpoint with protocol-aware `_meta` injection and SEP-2243 routing headers:

```python
@marker(tags=["perf"])
async def test_echo_under_agent_load():
    await assert_stateless_throughput(
        target_url="http://localhost:8080/mcp",
        tool_name="echo",
        arguments={"message": "hi"},
        duration_s=15,
        concurrency=250,
        min_rps=1000,
        max_p95_ms=40,
        max_p99_ms=50,
        max_error_rate=0.1,
    )
```

Certify adversarial SEP-2575 / SEP-2243 compliance separately:

```bash
mcp-test conformance stateless --url http://localhost:8080/mcp --generate-badge
```

See [design/RFC-006-stateless-mcp.md](design/RFC-006-stateless-mcp.md).

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
