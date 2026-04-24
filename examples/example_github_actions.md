# GitHub Action (one-line `mcp-test` in CI)

The repository ships a **composite action** you can call from a workflow. Inputs mirror the CLI: `server-command`, `transport`, `test-directory`, `config-file`, `report-format`, `harness-version`.

**Minimal job** (install harness from PyPI, run tests, upload JUnit):

```yaml
# .github/workflows/mcp-harness.yml
on: [push, pull_request]

jobs:
  mcp:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: vaquarkhan/mcp-test-harness/.github/actions/mcp-test@main
        with:
          server-command: "python -m my_server"
          test-directory: "tests/"
          report-format: "junit"
          harness-version: "latest"   # or "1.0.0" to pin

      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: mcp-junit
          path: mcp-test-report.xml
```

**Source of truth** in this repo: [`.github/actions/mcp-test/action.yml`](../.github/actions/mcp-test/action.yml)

**Cross-repo usage:** if you copy the path, use your fork’s `owner/repo@ref` or a **released tag** of this repository.

**Related:** [CI_AND_REPORTS.md](../docs/CI_AND_REPORTS.md) · [mcp_test_report_junit.yaml](mcp_test_report_junit.yaml)
