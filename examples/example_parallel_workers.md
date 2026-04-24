# Parallel execution

- **`test.parallel: true`** and **`test.workers: N`** in `mcp-test.yaml`, or **CLI** `--parallel --workers 4`
- **Same test file** stays on **one** worker so **per-module** fixtures and ordering remain coherent
- Set **`validate_schema_each_parallel_worker: false`** (default) to avoid duplicate post-connect work on every worker; worker 0 can do schema probes — see [example_schema_validation.md](example_schema_validation.md)

**Copy-paste config:** [sample_mcp_test.yaml](sample_mcp_test.yaml) (`parallel: true`, `workers: 4`)

```bash
mcp-test --parallel --workers 2
```
