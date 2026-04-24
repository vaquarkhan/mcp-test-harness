# Markers and `@skip`

- **`@marker(timeout=60, retry=1, tags=["smoke", "perf"], order=1)`** — filter with **`mcp-test -m smoke`** (tag or marker key)
- **`@skip(reason="…")`** — test is skipped with a reason

**Full copy-paste test snippets:** [patterns_mcp_test.md](patterns_mcp_test.md)  
**Performance / latency with `@marker(tags=["perf"])`:** [PERFORMANCE.md](../docs/PERFORMANCE.md)
