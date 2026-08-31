# Optional TOA verify after MCP Test Harness

Example only. Copy into your server repo as needed.

The harness gates protocol-aware tests. [TOA](https://github.com/Carmel-Labs-Inc/toa) (`toa/0.1`) verifies signed tool delivery evidence when you already have a `toa.json`. It is not a harness scenario and does not replace `mcp-test`.

```yaml
# .github/workflows/mcp-tests-and-toa.yml
name: MCP harness and optional TOA
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Test MCP Server
        uses: vaquarkhan/mcp-test-harness@v5.2.0
        with:
          server-command: "python my_server.py"
          test-directory: "tests/"

      # Optional: only runs when toa.json is present in the workspace.
      - name: Verify tool delivery attestation
        if: hashFiles('toa.json') != ''
        run: |
          pip install "git+https://github.com/Carmel-Labs-Inc/toa.git@5a1bf1cf6a15a4864ea809fe7b2a073f2cef4e22#subdirectory=python"
          toa-verify toa.json --require-emitter agentstatus --require-layer functional=pass --max-age 7d
```

Related: [example_github_actions.md](example_github_actions.md) · [docs/CI_AND_REPORTS.md](../docs/CI_AND_REPORTS.md)
