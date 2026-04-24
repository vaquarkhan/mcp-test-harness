# Architecture (visual)

This page is a **one-screen mental model** of how MCP Test Harness runs: config → discovery → scheduling → per-case execution over a real MCP **session** (stdio, SSE, or streamable HTTP).

## End-to-end flow

```mermaid
flowchart LR
  CLI["mcp-test CLI\n(cli.py)"]
  CFG["HarnessConfig\n(config.py)"]
  DISC["Test discovery\n(discovery.py)"]
  SCH["Scheduler\n(sequential / parallel)\n(scheduler.py)"]
  LCM["Server lifecycle\n(lifecycle.py)"]
  TR["Transport\n(transport.py)"]
  EX["Case executor\n(executor.py)"]
  TST["Test function\n+ fixtures"]
  CLI --> CFG --> DISC --> SCH
  SCH --> LCM
  LCM --> TR
  SCH --> EX
  EX --> TST
  LCM -->|"MCP session"| TST
```

- **One server per sequential run**, or **one server per worker** in parallel (tests from the same file stay on one worker; see [DECISIONS.md](DECISIONS.md)).
- **Schema checks** (optional) run right after connect via `scheduler` → [schema.py](../src/mcp_test_harness/schema.py).

## Data path (MCP)

```mermaid
sequenceDiagram
  participant T as mcp-test
  participant L as Lifecycle
  participant Tr as Transport
  participant S as MCP session
  participant M as test / assertions
  T->>L: start server, connect
  L->>Tr: stdio / SSE / HTTP
  Tr->>S: ClientSession
  L->>M: inject mcp_server / session fixture
  M->>S: list_tools, call_tool, read_resource, …
  M->>T: case result, reports
  L-->>T: shutdown, teardown
```

## Where to go next

| Topic | Document |
|--------|----------|
| Config keys and CLI | [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) |
| Assert helpers and snapshots | [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) |
| Ecosystem (Inspector, conformance, evals) | [COMPARISON.md](COMPARISON.md) |
| Docker / OCI | [DOCKER.md](DOCKER.md) |
| **Editors (VS Code, Cursor)** | [EDITORS.md](EDITORS.md) |

**Related:** [IMPLEMENTATION_CHECKLIST.md](IMPLEMENTATION_CHECKLIST.md) maps features to **source files** for maintainers.
