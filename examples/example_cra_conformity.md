# Example: CRA conformity matrix (`--cra-output`)

> [!TIP]
> **Feature highlight:** opt-in EU Cyber Resilience Act (Regulation EU 2024/2847) **technical evidence** packaging. Does not change transports, fixtures, or assertions. Guide: [CRA_COMPLIANCE.md](../docs/CRA_COMPLIANCE.md).

## Command

```bash
mcp-test --server-command "python -m your_server" \
  --cra-output reports/cra_conformity_matrix.json \
  --sarif-output reports/findings.sarif \
  tests/
```

## Config

```yaml
# mcp-test.yaml
report:
  format: json
  output: reports/mcp-test.json
  cra_output: reports/cra_conformity_matrix.json
  sarif_output: reports/findings.sarif
```

## Tag mapping

| Marker tags | CRA theme (summary) |
|-------------|---------------------|
| `security`, `sec` | Vulnerability-handling evidence |
| `chaos`, `resiliency` | Resilience under attack/outage |
| `perf`, `performance` | Availability / load SLOs |
| `smoke`, `regression`, `snapshot` | Integrity of functions |
| `schema`, `protocol` | Secure defaults |

## Related

- Vulnerability disclosure: [`.github/SECURITY.md`](../.github/SECURITY.md)
- SBOM on `v*` releases: CycloneDX artifacts from publish workflows
- Diagram: [docs/images/cra-evidence-flow.svg](../docs/images/cra-evidence-flow.svg)
