from mcp_test_harness import assert_latency, marker


@marker(tags=["perf"], timeout=60)
async def test_performance_latency_p95(mcp_server):
    await assert_latency(
        mcp_server,
        "echo",
        {"text": "perf-check"},
        max_ms=250,
        aggregate="p95",
        runs=20,
        warmup=3,
    )


@marker(tags=["perf"], timeout=60)
async def test_performance_latency_p99(mcp_server):
    await assert_latency(
        mcp_server,
        "echo",
        {"text": "perf-check"},
        max_ms=400,
        aggregate="p99",
        runs=30,
        warmup=5,
    )
