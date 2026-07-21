# RFC-006: Stateless MCP (SEP-2575) conformance and throughput

**Status:** Implemented (experimental — targets MCP **2026-07-28** draft / RC)  
**Related:** [RFC-002](RFC-002-conformance-levels.md) (stateful Boot→Resilient levels), [PERFORMANCE.md](../PERFORMANCE.md)

## Problem

MCP **2026-07-28** (SEP-2575) makes Streamable HTTP **stateless by default**:

- No mandatory `initialize` / `initialized` handshake
- No protocol-level `Mcp-Session-Id`
- Every POST carries client context in `params._meta` (`io.modelcontextprotocol/*`)
- SEP-2243 routing headers: `MCP-Protocol-Version`, `Mcp-Method`, `Mcp-Name`
- `server/discover` replaces handshake for capability discovery

Existing harness flows remain **stateful** (stdio, SSE, session HTTP via MCP SDK + `ServerLifecycleManager`).

## Dual-mode model

| Mode | Transport | Discovery | Load / perf | Conformance |
|------|-----------|-----------|-------------|-------------|
| **Stateful** | stdio, sse, http (SDK session) | `initialize` handshake | `assert_throughput(session, …)` | `mcp-test try` (RFC-002 Boot→Protocol) |
| **Stateless** | Streamable HTTP POST only | `server/discover` | `assert_stateless_throughput(url, …)` | `mcp-test conformance stateless --url …` |

Both modes can coexist in one repo: gate stateful paths in CI with `mcp-test` + fixtures; gate stateless HTTP endpoints with the SEP-2575 suite.

## SEP-2575 conformance suite

Command:

```bash
mcp-test conformance stateless --url http://localhost:8080/mcp \
  --protocol-version 2026-07-28 \
  --generate-badge
```

Adversarial checks (expect **HTTP 400** unless noted):

1. **Baseline discover** — valid `server/discover` → **200**, `supportedVersions` + `capabilities`
2. **Missing `MCP-Protocol-Version` header**
3. **Header vs `_meta` version mismatch** → JSON-RPC `-32022` + `error.data.supported` / `requested`
4. **Unsupported version** (`9999-99-99`) → strict `-32022` schema
5. **Missing `Mcp-Method` header** (SEP-2243)
6. **Mismatched `Mcp-Method`** vs JSON-RPC `method`

Pass → print **MCP Stateless Compliant** badge markdown for README.

Implementation: `src/mcp_test_harness/stateless/conformance.py`

## Hyperscale throughput (stateless)

Session-based `assert_throughput` spins up MCP sessions (handshake per worker in parallel mode). Stateless load skips handshake and fires self-contained POSTs:

```python
from mcp_test_harness import assert_stateless_throughput

@pytest.mark.perf
async def test_echo_under_agent_load():
    await assert_stateless_throughput(
        target_url="http://localhost:8080/mcp",
        tool_name="echo",
        arguments={"message": "hi"},
        duration_s=15,
        concurrency=250,
        min_rps=1000,
        max_p99_ms=50,
        max_error_rate=0.1,
    )
```

Implementation: `src/mcp_test_harness/stateless/throughput.py` (httpx async, protocol-aware error detection).

## Dependencies

Uses **httpx** (already pulled in by the `mcp` SDK). No new required packages.

## Spec drift

The 2026-07-28 spec is pre-release. Error codes, header names, and `DiscoverResult` fields may change. The suite version is pinned via `--protocol-version` and constants in `stateless/constants.py`.

## Future work

- Auto-detect stateful vs stateless from `server/discover` probe in `mcp-test try`
- SARIF / JSON report attachment for stateless conformance runs
- HTML report panel for stateless badge + throughput SLOs
- Official MCP SDK stateless client adapter in `transport.py` when SDK ships
