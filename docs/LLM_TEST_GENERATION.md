# LLM-assisted test generation: good idea or bad?

**Short answer:** using an **LLM in the loop while you write** (editor assistant, “generate a draft `assert_tool_call` test”) is often **useful** if a **human reviews** the result. Wiring **“any LLM”** to **automatically** create and **trust** test cases in CI, with **no review**, is usually a **bad fit** for what **MCP Test Harness** is for.

## What this project optimizes for

- **Deterministic, developer-owned tests** that run the **same way** on every commit.
- **No LLM in the `mcp-test` execution path** — your CI calls `call_tool` and assertions **directly**; the outcome does not depend on a model, API, or network at test time. That is a **product choice**, not a limitation (see [COMPARISON.md](COMPARISON.md)).

So: **“auto-create tests from a connected LLM”** as a **default, trusted pipeline** would **blur** the line between *regression tests* and *LLM evals*.

## When LLM help is a **good** idea (recommended pattern)

| Practice | Why |
|----------|-----|
| **Draft only** | Use a copilot / chat model to **suggest** `async def test_…(mcp_server):` and `assert_tool_call` given your server’s tool list. |
| **Always review** | Check tool names, arguments, and invariants. Fix hallucinated names and add **snapshots** / **schema** checks where the model skipped them. |
| **Start from a scaffold** | `mcp-test init` + [examples](../examples/) give a **correct** template; the LLM fills in the middle. |
| **Keep generation out of CI** | The **artifact** in Git is **plain Python** under `tests/`; CI runs `mcp-test` only. No API keys or model calls in the pipeline. |

## When it is a **bad** or risky idea

| Anti-pattern | Risk |
|--------------|------|
| **“Fire and forget”** generated tests in `main` | Flaky or wrong **tool** names; tests that “pass” without asserting real invariants. |
| **Unreviewed** LLM code with **network** in tests | Accidental `pip install` or data exfil patterns if the model is unbounded. |
| **Confusing harness with evals** | If you need **“does the model use my MCP well?”** use tools built for that ([mcp-eval](https://mcp-eval.ai), [testmcpy](https://github.com/preset-io/testmcpy)) — see [COMPARISON.md](COMPARISON.md). The harness is for **your** **deterministic** checks. |
| **Putting the LLM inside `mcp-test` core** | Would add non-determinism, cost, and supply-chain issues to a tool meant for **reliable** CI. |

## If you want “instructions” for your team

You can add an **internal** prompt or `CONTRIBUTING` snippet (not shipped as core harness code), for example:

1. “Given this `mcp-test.yaml` and `list_tools` output, **propose** one smoke test and one negative test; use **harness** imports only: `mcp_test_harness` …”
2. “**Do not** add network clients or new dependencies; use only `assert_tool_call` / `assert_tool_list` / …”
3. “Output must be a **diff** the engineer applies after review.”

That keeps **MCP Test Harness** **predictable** while still getting a speed-up from an LLM **outside** the runtime.

## Related

- [COMPARISON.md](COMPARISON.md) — harness vs mcp-eval / testmcpy / Conformance
- [COLLECTIONS.md](COLLECTIONS.md) — multi-step flows without an LLM
- [examples/README.md](../examples/README.md) — patterns to show an assistant
