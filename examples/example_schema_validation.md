# JSON-RPC & MCP schema validation

When **`schema_validation: true`** (the default) in `mcp-test.yaml` / TOML, the harness runs **MCP-appropriate checks** on JSON-RPC and known objects during the lifecycle (e.g. after `initialize`, for `list_tools` / `list_resources` / `list_prompts` shapes, and a best-effort `call_tool` **probe** so tool **content** items match the expected schema).

Tighten or relax behavior with:

```yaml
schema_validation: true
validate_schema_each_parallel_worker: false
schema_probe_call_tool: true
```

Turn **`schema_probe_call_tool`** off if the probe is incompatible with a very unusual server; see [DEVELOPER_GUIDE.md – configuration](../docs/DEVELOPER_GUIDE.md#part-3-configuration).

**Validate your config file:** [validate_mcp_test_config.py](validate_mcp_test_config.py)
