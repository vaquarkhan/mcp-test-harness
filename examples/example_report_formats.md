# Report formats (JUnit, JSON, HTML)

Choose **one** `report.format` per run. Each file below is a **complete minimal** `mcp-test.yaml` you can copy (adjust `server.command`).

| Format | When to use | Example file |
|--------|-------------|-------------|
| **junit** | GitHub Actions, Jenkins, GitLab (JUnit **XML** artifact) | [mcp_test_report_junit.yaml](mcp_test_report_junit.yaml) |
| **json** | Custom dashboards, full metadata in one file | [mcp_test_report_json.yaml](mcp_test_report_json.yaml) |
| **html** | Human-readable page in a browser or uploaded as artifact | [mcp_test_report_html.yaml](mcp_test_report_html.yaml) |

**CLI (overrides file):** `mcp-test --report-format junit --report-output reports/out.xml .`

**CI publishing guidance:** [CI_AND_REPORTS.md](../docs/CI_AND_REPORTS.md)
