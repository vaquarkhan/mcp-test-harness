# Report formats (JUnit, JSON, HTML)

Choose **one** `report.format` per run. Each file below is a **complete minimal** `mcp-test.yaml` you can copy (adjust `server.command`).

| Format | When to use | Example file |
|--------|-------------|-------------|
| **junit** | GitHub Actions, Jenkins, GitLab (JUnit **XML** artifact) | [mcp_test_report_junit.yaml](mcp_test_report_junit.yaml) |
| **json** | Custom dashboards, full metadata in one file | [mcp_test_report_json.yaml](mcp_test_report_json.yaml) |
| **html** | Human-readable **dashboard** (self-contained HTML, no network; inspired by portaled CI / quality UIs) | [mcp_test_report_html.yaml](mcp_test_report_html.yaml) · sample [feature-demo/reports/sample_mcp_test_report.html](feature-demo/reports/sample_mcp_test_report.html) |

**CLI (overrides file):** `mcp-test --report-format junit --report-output reports/out.xml .`

**Regenerate the static HTML sample** (optional): `python examples/feature-demo/reports/build_sample_html.py` — lives under [feature-demo](feature-demo/README.md).

**CI publishing guidance:** [CI_AND_REPORTS.md](../docs/CI_AND_REPORTS.md)
