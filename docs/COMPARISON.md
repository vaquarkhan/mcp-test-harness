# Ecosystem: MCP Test Harness and related tools

MCP Test Harness is **deterministic, developer-written CI automation** over a real MCP client session. It does **not** require an LLM in the test loop.

Use **more than one tool** across the lifecycle: config security at dev time, server gates at merge time, Bastion at runtime.

## Comparison table

| Project | Primary focus | Typical use | vs Harness |
|--------|----------------|-------------|------------|
| **MCP Test Harness** (this repo) | Pytest-style CI: functional + regression + perf + security payloads | “Server passes our contract on every commit” | — |
| **[mcp-shark](https://github.com/mcp-shark/mcp-shark)** | IDE **config** security, toxic flows, live traffic forensics | “Is my Cursor/Windsurf MCP setup safe?” | **Complement** — config layer, not server CI |
| **MCP Inspector** | Manual GUI debugging | Local exploration | **Complement** — not CI |
| **MCP Conformance** | Protocol compliance suites | “Does our SDK match the spec?” | **Complement** — spec vs product regression |
| **mcp-eval** | Agent + LLM judges, OTel metrics | “Does an agent use our server well?” | **Adjacent** — stochastic, not merge gates |
| **testmcpy** | YAML + LLM tool-calling evals | Model comparison | **Adjacent** — LLM-in-loop |
| **MCPMark** | Model benchmarks on real services | Research / model quality | **Different question** |
| **Viper-MCP / mcp-testbench** | Stochastic fuzzing, crashes, injections | Find vulnerabilities | **Complement** — no SLO gates |
| **k6 / JMeter / Gatling** | Distributed HTTP load | Datacenter-scale RPS | **Complement** — no MCP lifecycle |
| **[MCP-Bastion](https://github.com/vaquarkhan/MCP-Bastion)** | Runtime WAF: injection, PII, rate limits | Production protection | **Pair** — test in CI, protect live |

Full positioning: [POSITIONING.md](POSITIONING.md).

## How tools fit together

```mermaid
flowchart TB
  subgraph dev [Developer machine]
    SHARK[mcp-shark scan / proxy]
    INS[MCP Inspector]
  end
  subgraph ci [CI pipeline]
    HARNESS[mcp-test-harness]
  end
  subgraph prod [Production]
    BASTION[MCP-Bastion]
    SERVER[MCP Server]
  end
  SHARK -->|config + traffic audit| dev
  INS -->|manual debug| dev
  HARNESS -->|gate merge| ci
  BASTION -->|runtime defense| SERVER
```

| Question | Tool |
|----------|------|
| Is my **IDE config** risky? | mcp-shark |
| Does my **server** pass **our** tests? | MCP Test Harness |
| Is the implementation **spec-correct**? | MCP Conformance |
| How does an **LLM agent** behave? | mcp-eval, testmcpy |
| Is production **protected**? | MCP-Bastion |

## MCP Inspector pairing (local sandbox → CI)

[MCP Test Harness](https://github.com/vaquarkhan/mcp-test-harness) and the [Official MCP Inspector](https://modelcontextprotocol.io/docs/tools/inspector) share the same protocol surface; they are a classic **local sandbox** vs **continuous integration** split, not competitors.

### What the harness automates from the Inspector workflow

| Inspector (manual) | Harness (automated) |
|--------------------|---------------------|
| Handshake & capability discovery (tools / resources / prompts) | Same JSON-RPC lifecycle in setup / `mcp-test try` / schema probes |
| Mock LLM host UI to exercise server endpoints | Headless deterministic client session (`mcp_server` fixture) |
| Connect via stdio / SSE / HTTP | Same transports via CLI flags or `mcp-test.yaml` |

The harness exists so you stop re-clicking the Inspector for every regression: the payloads you typed once become assertions that run on every PR.

### Recommended loop

1. **Dev sandbox (Inspector)** — While writing a new tool, run the Inspector locally for smoke checks and ad-hoc JSON payloads.
2. **Graduate to code (Harness)** — When the tool behaves, encode those inputs as deterministic tests:

```python
from mcp_test_harness.assertions import assert_tool_call

async def test_weather_tool(mcp_server):
    result = await assert_tool_call(
        mcp_server,
        "get_weather",
        {"location": "Chicago"},
    )
    assert "temperature" in str(result)
```

3. **CI + troubleshoot** — GitHub Actions runs `mcp-test` (or `uses: vaquarkhan/mcp-test-harness@v3.0.7`). On failure, use harness output for schema/assertion detail; reopen the Inspector locally when you need raw transport traffic.

Also: `mcp-test try --server-command "..."` for a zero-config Boot/Protocol probe before you write a full suite.

### Record to suite (RFC-001)

After the Inspector smoke check, skip hand-writing the first tests:

```bash
mcp-test record --server-command "python my_server.py" --out tests/test_mcp_recorded.py
mcp-test tests/test_mcp_recorded.py
```

Or feed a JSON cassette of `{tool, arguments}` pairs with `--from-json`. See [RFC-001](design/RFC-001-record-to-suite.md).

## mcp-shark pairing (recommended)

[mcp-shark](https://github.com/mcp-shark/mcp-shark) scans **static IDE configs** (secrets, OWASP rules, toxic cross-server flows) and optionally captures **live JSON-RPC** via a local proxy. It does **not** replace server functional tests.

```yaml
# .github/workflows/mcp-quality.yml
jobs:
  config-security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npx @mcp-shark/mcp-shark scan --ci --format sarif
  server-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: vaquarkhan/mcp-test-harness@v3.0.7
        with:
          server-command: "python -m my_server.mcp"
          test-directory: tests/
```

**License note:** mcp-shark uses a **non-commercial** license. Integrate via CLI sidecar in CI; do not embed its code or rule packs in this MIT project without permission.

## Postman / load testing

**Collections** (declarative YAML flows) are roadmap — see [COLLECTIONS.md](COLLECTIONS.md). Today: **Python** multi-step tests.

**Cluster-scale load** stays outside core; use k6/JMeter for extreme RPS. Harness owns **MCP-aware SLO gates** (`assert_latency`, session `assert_throughput`, and SEP-2575 `assert_stateless_throughput` with `min_rps`, `max_p99_ms`, `max_error_rate`). Stateless certification: `mcp-test conformance stateless` ([RFC-006](design/RFC-006-stateless-mcp.md)).

## LLM test generation

Harness is for **deterministic** CI. External LLMs may **draft** tests with human review — see [LLM_TEST_GENERATION.md](LLM_TEST_GENERATION.md).

## Companion: MCP-Bastion

Bastion = **runtime security**. Harness = **test automation**. See root [README.md](../README.md#security-testing-with-mcp-bastion).
