# Platform QA demo pack (v1.3)

Runnable examples for **MCP trace timelines**, **protocol-aware chaos**, and **`mcp-test generate`** scaffolding.

| Feature | Example doc | Runnable tests |
|---------|-------------|----------------|
| **MCP trace** | [example_mcp_trace.md](../../example_mcp_trace.md) | `test_echo_records_mcp_trace` |
| **Chaos faults** | [example_chaos_testing.md](../../example_chaos_testing.md) | `test_platform_qa_demo.py` (`-m chaos`) |
| **Generate scaffold** | [example_generate_scaffold.md](../../example_generate_scaffold.md) | [sample_mcp_generated.example.py](sample_mcp_generated.example.py) |

## Files

- `test_platform_qa_demo.py` — trace + chaos patterns (delay, 503, truncate, schema drift)
- `mcp_test_platform_qa_demo.yaml` — HTML report config (traces render in timeline UI)
- `sample_mcp_generated.example.py` — static sample of `mcp-test generate` output
- `reports/` — where HTML artifacts land after a run

## Run (point at your MCP server)

```bash
mcp-test --server-command "python -m your_server" examples/feature-demo/platform-qa
```

With config (writes HTML + trace timeline):

```bash
mcp-test -c examples/feature-demo/platform-qa/mcp_test_platform_qa_demo.yaml
```

Chaos tests only:

```bash
mcp-test -m chaos --server-command "python -m your_server" examples/feature-demo/platform-qa
```

## Generate draft tests from your server

```bash
mcp-test generate \
  --server-command "python -m your_server" \
  --tests-subdir examples/feature-demo/platform-qa \
  --filename test_mcp_generated.py \
  --drift-report examples/feature-demo/platform-qa/reports/tool-drift.json
```

Review output, remove `@skip` on edge cases you care about, then run `mcp-test` on the folder.

## Inspect traces

After an HTML run, open `reports/platform-qa-demo.html` and expand any test — the **MCP trace timeline** lists each JSON-RPC call with timestamps.

**Up:** [feature-demo README](../README.md) · [FEATURES_INDEX](../../FEATURES_INDEX.md)
