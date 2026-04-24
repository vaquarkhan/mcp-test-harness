# Ecosystem: MCP Test Harness and related tools

MCP Test Harness is aimed at **deterministic, developer-written tests** that drive an MCP **client session** in CI: `call_tool`, snapshots, schema checks, and [latency budgets](PERFORMANCE.md). It does **not** require a large language model in the test loop.

Other projects solve different problems. Use the table below to pick the right tool (often **more than one**).

## Comparison

| Project | Primary focus | Typical use | Link |
|--------|----------------|-------------|------|
| **MCP Test Harness** (this repo) | Pytest-style automation, `mcp-test` CLI, snapshots, `assert_*`, [parallel runs](DEVELOPER_GUIDE.md) | “Our server does X on every commit”; fast CI; no LLM required | [README.md](../README.md) |
| **MCP Conformance** | **Protocol compliance** (initialize, tools, resources, auth scenarios) for **client and server** implementations | “Does our SDK/server match the spec?”; baseline known failures | [github.com/modelcontextprotocol/conformance](https://github.com/modelcontextprotocol/conformance) |
| **mcp-eval** | **Agents + real MCP**; OpenTelemetry metrics; `Expect` API; **LLM judges**; dataset-style runs | “Does a model-driven agent use our server correctly in production-like conditions?” | [mcp-eval.ai](https://mcp-eval.ai) · [github.com/lastmile-ai/mcp-eval](https://github.com/lastmile-ai/mcp-eval) |
| **MCPMark** | **Benchmark** for **models** using multiple real MCP services (Notion, GitHub, etc.) | Research / model quality; pass@k-style aggregates | [github.com/eval-sys/mcpmark](https://github.com/eval-sys/mcpmark) |
| **testmcpy** | **YAML**-driven cases with an **LLM** calling your MCP service; model comparison, evaluators | “Which model calls the right tool with the right args?” (product + domain specific) | [github.com/preset-io/testmcpy](https://github.com/preset-io/testmcpy) |

**MCP Inspector** (often used during development) is **manual** and **not** a substitute for automated CI; see the root [README.md](../README.md#why-mcp-test-harness-vs-mcp-inspector).

## How tools fit together

- **Conformance** answers: *Is the implementation spec-correct?*
- **MCP Test Harness** answers: *Does **our** server behave the way **our** tests encode (regression, contracts, SLO-style latency where we assert it)?*
- **mcp-eval / testmcpy** answer: *How does an **LLM** or **agent** behave when using MCP?*
- **MCPMark** answers: *How capable are **models** on realistic multi-tool tasks?*

None of these replace the others for their core question.

## Postman- or JMeter-style ideas (not in core today)

**Collections** (declarative multi-step flows + environments) and **load/throughput** tools (concurrency, long-run stress) are common asks. They are **not** part of the harness yet; today, multi-step behavior is expressed in **Python** tests, and [PERFORMANCE.md](PERFORMANCE.md) documents **single-client** latency (`assert_latency`), not cluster-scale load testing. If you add these, treat them as optional surfaces (e.g. a `run` / `load` subcommand) so default **pytest** CI stays fast and stable.

## Companion: MCP-Bastion

[MCP-Bastion](https://github.com/vaquarkhan/MCP-Bastion) is **runtime security** (e.g. prompt injection, PII, rate limits). The harness is **test automation**; Bastion is **protection in production**.
