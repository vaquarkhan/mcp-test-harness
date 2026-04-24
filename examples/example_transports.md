# Transports: stdio, SSE, streamable HTTP

| Transport | `server` block | When |
|-----------|----------------|------|
| **stdio** (default) | `transport: stdio` + `command: …` (child process) | Local MCP servers started as a subprocess |
| **sse** | `transport: sse` + `command` = base URL, plus `transport_options` | **Remote** server (SSE) |
| **http** | `transport: http` + URL + `transport_options` (path, headers) | **Streamable HTTP** endpoint |

**stdio example:** [sample_mcp_test.yaml](sample_mcp_test.yaml) (default transport).

**Remote examples (placeholders):**
- [mcp_test_transport_sse.example.yaml](mcp_test_transport_sse.example.yaml)
- [mcp_test_transport_http.example.yaml](mcp_test_transport_http.example.yaml)

**Full key reference:** [DEVELOPER_GUIDE.md – configuration](../docs/DEVELOPER_GUIDE.md#part-3-configuration) · [validate_mcp_test_config.py](validate_mcp_test_config.py) to validate a file
