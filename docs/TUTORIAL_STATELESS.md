# Tutorial: Stateless MCP (SEP-2575) conformance & hyperscale throughput

Author: [Vaquar Khan](https://github.com/vaquarkhan)

> [!NOTE]
> MCP **2026-07-28** makes Streamable HTTP **stateless by default** (SEP-2575 / SEP-2567 / SEP-2243). This tutorial covers the **new** dual-mode path. For classic **stateful** servers (stdio + `initialize` handshake), use the main [TUTORIAL.md](TUTORIAL.md).

By the end you will:

1. Certify a Streamable HTTP endpoint with `mcp-test conformance stateless`
2. Gate agent-scale load with `assert_stateless_throughput`
3. Keep **stateful** CI unchanged (`mcp-test try`, `assert_throughput` / `assert_load_phases`)

Design background: [design/RFC-006-stateless-mcp.md](design/RFC-006-stateless-mcp.md).

---

## Prerequisites

- Python 3.10+
- A **stateless** MCP server URL (e.g. `http://localhost:8080/mcp`) that speaks draft **2026-07-28**
- `pip install -e ".[dev]"` from this repo (or `pip install mcp-test-harness`)

Confirm CLI:

```bash
mcp-test --version
mcp-test conformance --help
```

---

## Dual-mode cheat sheet

| Goal | Stateful (existing) | Stateless (this tutorial) |
|------|---------------------|---------------------------|
| Zero-config probe | `mcp-test try --server-command "…"` | `mcp-test conformance stateless --url …` |
| Functional tests | `mcp_server` fixture + `assert_tool_call` | Raw HTTP tools/call with `_meta` (suite covers discover + headers) |
| Load / SLO | `assert_throughput` / `assert_load_phases` (session) | `assert_stateless_throughput(url, …)` |
| Session | `initialize` + optional session id | None — each POST is self-contained |

Both can live in one repo: gate stdio servers with fixtures; gate cloud HTTP MCP with the SEP-2575 suite.

---

## 1. Certify SEP-2575 / SEP-2243 compliance

```bash
mcp-test conformance stateless \
  --url http://localhost:8080/mcp \
  --protocol-version 2026-07-28 \
  --generate-badge \
  --verbose
```

What the gate attacks (expect **HTTP 400** unless noted):

| Check | Intent |
|-------|--------|
| Baseline Discover | Valid `server/discover` → **200** + `supportedVersions` + `capabilities` |
| Missing Protocol Header | Omit `MCP-Protocol-Version` |
| Mismatched Protocol Version | Header ≠ `_meta` → JSON-RPC **-32022** |
| Unsupported Protocol Version Schema | Version `9999-99-99` → `-32022` with `error.data.supported` / `requested` |
| SEP-2243 Missing Mcp-Method | Omit routing header |
| SEP-2243 Mismatched Mcp-Method | Header contradicts JSON-RPC `method` |

On success you get a README badge snippet:

```markdown
![MCP Stateless Compliant](https://img.shields.io/badge/MCP_Stateless-Compliant-brightgreen?style=for-the-badge)
```

Exit code **0** = certified; **1** = non-compliant (fix headers / error schema before merge).

---

## 2. Add a CI performance gate (stateless)

Create `tests/test_stateless_perf.py`:

```python
import pytest
from mcp_test_harness import assert_stateless_throughput, marker


@marker(tags=["perf", "stateless"])
@pytest.mark.asyncio
async def test_echo_under_agent_load():
    """Simulates concurrent agent tool calls without initialize handshake."""
    await assert_stateless_throughput(
        target_url="http://localhost:8080/mcp",
        tool_name="echo",
        arguments={"message": "hi"},
        duration_s=10,
        concurrency=50,
        min_rps=100.0,
        max_p95_ms=150.0,
        max_p99_ms=200.0,
        max_error_rate=1.0,  # percent
    )
```

Run:

```bash
mcp-test -m perf --server-command "python my_stateful_server.py"  # stateful path unchanged
# Stateless load does not need --server-command; it hits --url directly via pytest:
pytest tests/test_stateless_perf.py -q
```

Or from your own pytest job after installing the harness:

```bash
pytest tests/test_stateless_perf.py -m "perf and stateless"
```

---

## 3. Keep stateful conformance in the same pipeline

Do **not** replace `mcp-test try` for stdio / session servers:

```bash
# Stateful Boot → Protocol (RFC-002)
mcp-test try --server-command "python my_server.py"

# Stateless SEP-2575 matrix (RFC-006)
mcp-test conformance stateless --url "$MCP_HTTP_URL" --generate-badge
```

Example GitHub Actions job sketch:

```yaml
- name: Stateful conformance
  run: mcp-test try --server-command "python -m my_package.mcp"

- name: Stateless conformance
  run: mcp-test conformance stateless --url ${{ secrets.MCP_HTTP_URL }} --generate-badge

- name: Suite (functional + perf tags)
  run: mcp-test -m "not stateless" --server-command "python -m my_package.mcp" tests/
```

---

## 4. What “good” looks like

- **Stateful** servers keep using lifecycle fixtures; nothing in existing `assert_*` APIs changed.
- **Stateless** HTTP servers pass all six adversarial checks and meet RPS / p99 / error-rate SLOs.
- README shows both badges when applicable: RFC-002 level + Stateless Compliant.

---

## Next reading

| Doc | Why |
|-----|-----|
| [RFC-006](design/RFC-006-stateless-mcp.md) | Spec matrix + architecture |
| [PERFORMANCE.md](PERFORMANCE.md) §4–4.2 | `assert_throughput` / `assert_load_phases` vs `assert_stateless_throughput` |
| [examples/example_stateless_conformance.md](../examples/example_stateless_conformance.md) | Copy-paste CLI |
| [examples/example_stateless_throughput.md](../examples/example_stateless_throughput.md) | Copy-paste pytest |
| [TUTORIAL.md](TUTORIAL.md) | Stateful walkthrough from scratch |

---

## License

Non-commercial use with mandatory attribution. See [LICENSE](../LICENSE).

Attribution: Vaquar Khan — https://github.com/vaquarkhan
