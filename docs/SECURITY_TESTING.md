# Security testing

MCP Test Harness catches **security regressions in CI** using deterministic, MCP-aware tests — without becoming a runtime WAF.

## Shipped capabilities

### Auth and boundaries

- `assert_tool_denied` — protected calls must be rejected
- `assert_authorization_boundary` — allowed context succeeds, denied context fails

### Payload packs (`security_payloads.py`)

Tag tests with `@marker(tags=["security"])`:

| Helper | Purpose |
|--------|---------|
| `assert_injection_blocked` | Prompt-injection corpus; fails on verbatim echo |
| `assert_path_traversal_blocked` | Path traversal payloads; fails on sensitive content |
| `assert_no_secret_leak` | Scans output for API keys, JWT, private keys, etc. |
| `run_security_payload_pack` | Runs injection (+ optional path) checks in one call |

Corpora: `PROMPT_INJECTION_PAYLOADS`, `PATH_TRAVERSAL_PAYLOADS`, `SECRET_LEAK_PATTERNS`.

### Resiliency (related)

- `assert_degrades_gracefully`, `assert_reconnects`, `assert_survives_crash` — tag `@marker(tags=["resiliency"])`

### Reporting

Security tests appear in the **unified portal** (HTML/JSON `unified_summary.categories.security`) and contribute to the overall CI gate.

**Declarative quality gate** (opt-in — still CI-native; not a hosted dashboard):

```yaml
# mcp-test.yaml
quality_gate:
  require_security_tests: true   # fail if no @marker(tags=["security"]) cases ran
  fail_on_severity: high          # fail when security findings ≥ this severity
```

JSON/HTML emit `unified_summary.quality_gate` (`status`, `reasons`, findings counts, catalogue size) alongside the legacy `gate` field and existing SARIF/HTML artifacts. Exit code is `1` when the quality gate fails (including “no security tests” when required).

**SARIF export** (GitHub Code Scanning):

```bash
mcp-test --report-format sarif --report-output mcp-security.sarif
# or alongside JUnit:
mcp-test --report-format junit --report-output report.xml --sarif-output mcp-security.sarif
```

**CRA conformity matrix** (opt-in Annex I evidence packaging — see [CRA_COMPLIANCE.md](CRA_COMPLIANCE.md)):

```bash
mcp-test --cra-output reports/cra_conformity_matrix.json -m security
```

**OWASP / MCP / LLM rule catalogue** (`security_rules.py`) attaches metadata to failed security tests in JSON (`security_findings[].rule`) and SARIF (`ruleId`, `properties.owasp_id`). Frameworks: `OWASP-MCP`, `OWASP-LLM`, `agentic-security`, `general-security`. Tag tests explicitly, e.g. `@marker(tags=["security", "mcp06"])` or `llm01`, `agency`, `exfiltration`.

> **Not `mcplint`:** the optional `mcp-test-harness[mcplint]` extra is only a Bastion **version pin helper**. The quality gate lives in the core harness (`mcp-test` + `quality_gate:`).

**PR comments** — enable in the GitHub Action with `pr-comment: true` or write locally:

```bash
mcp-test --pr-summary-output mcp-pr-summary.md
```

## Example

```python
from mcp_test_harness import marker, run_security_payload_pack, assert_authorization_boundary

@marker(tags=["security", "smoke"])
async def test_chat_injection_blocked(mcp_server):
    await run_security_payload_pack(
        mcp_server, "chat",
        injection_argument="input",
        path_argument="path",
    )

@marker(tags=["security"])
async def test_admin_boundary(mcp_server):
    await assert_authorization_boundary(
        mcp_server, "delete_user",
        allowed_arguments={"role": "admin", "id": "1"},
        denied_arguments={"role": "guest", "id": "1"},
    )
```

## CI usage

| Track | When | Command |
|-------|------|---------|
| Security smoke | Every PR | `mcp-test -m security` |
| Full payload suite | Nightly / main | All security-tagged tests |
| Config audit (optional) | PR | `npx @mcp-shark/mcp-shark scan --ci` — see [COMPARISON.md](COMPARISON.md) |

## Integration model

- Core assertions stay **deterministic and fast**.
- Heavy scanners (e.g. Presidio PII) → plugins or [MCP-Bastion](https://github.com/vaquarkhan/MCP-Bastion).
- Runtime protection → Bastion in production; harness **verifies** defenses in CI.

## EU AI Act and governance

Demo pack: `examples/feature-demo/eu-ai-act/` — auth boundaries, deterministic checks, report artifacts.

Test artifacts support compliance **evidence packages**; they supplement — not replace — legal and risk review. See [ENTERPRISE_GOVERNANCE.md](ENTERPRISE_GOVERNANCE.md).

## Roadmap (remaining)

- Optional toxic-flow heuristics when multiple tool sources are detected
- Deeper integration with external fuzz engines (delegate, not embed)
