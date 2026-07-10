# GitHub Action (MCP tests + conformance level)

The repository ships a **composite action** you can call from a workflow. Inputs mirror the CLI: `server-command`, `transport`, `test-directory`, `config-file`, `report-format`, `harness-version`, plus:

- `pr-comment` — post PR summary including **RFC-002 conformance level**
- `try-mode` — run `mcp-test try` (zero-config probe) instead of a test suite
- Outputs: `test-result`, `conformance-level`, `conformance-level-num`

**Minimal job** (install harness from PyPI, run tests, upload JSON + level):

```yaml
# .github/workflows/mcp-harness.yml
on: [push, pull_request]

jobs:
  mcp:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: vaquarkhan/mcp-test-harness@v3.0.2
        id: mcp
        with:
          server-command: "python -m my_server"
          test-directory: "tests/"
          harness-version: "latest"   # or pin e.g. "3.0.2"
          pr-comment: "true"

      - run: echo "Conformance ${{ steps.mcp.outputs.conformance-level }}"

      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: mcp-json
          path: mcp-test-report.json
```

**Zero-config conformance (dogfood a public server):**

```yaml
- uses: vaquarkhan/mcp-test-harness@v3.0.2
  with:
    try-mode: "true"
    server-command: "uvx awslabs.roda-mcp-server@latest"
    pr-comment: "true"
```

**Source of truth:** root [`action.yml`](../action.yml) (Marketplace / `owner/repo@tag`) and mirror [`.github/actions/mcp-test/action.yml`](../.github/actions/mcp-test/action.yml) (`owner/repo/.github/actions/mcp-test@tag`).

**Marketplace:** listed at [github.com/marketplace/actions/mcp-test-harness](https://github.com/marketplace/actions/mcp-test-harness). Pin `@v3.0.2` (or `@main`).

**Related:** [CI_AND_REPORTS.md](../docs/CI_AND_REPORTS.md) · [RFC-002](../docs/design/RFC-002-conformance-levels.md) · [mcp_test_report_junit.yaml](mcp_test_report_junit.yaml)
