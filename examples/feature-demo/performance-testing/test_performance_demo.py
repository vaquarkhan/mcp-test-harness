from mcp_test_harness import assert_latency, assert_load_phases, assert_throughput, marker


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


@marker(tags=["perf", "load"], timeout=60)
async def test_performance_throughput_burst(mcp_server):
    await assert_throughput(
        mcp_server,
        "echo",
        {"text": "load"},
        concurrent=4,
        total_calls=16,
        max_p95_ms=500.0,
        max_error_rate=0.05,
        warmup=1,
    )


@marker(tags=["perf", "load"], timeout=90)
async def test_performance_load_ramp(mcp_server):
    await assert_load_phases(
        mcp_server,
        "echo",
        {"text": "load"},
        phases=[
            {"name": "warmup", "concurrent": 2, "total_calls": 4, "warmup": True},
            {"name": "c4", "concurrent": 4, "total_calls": 8},
        ],
        max_p99_ms=800.0,
        max_error_rate=0.05,
    )
