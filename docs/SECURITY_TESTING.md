# Security testing

MCP Test Harness catches **security regressions in CI** using deterministic, MCP-aware tests — without becoming a runtime WAF.

**Why security-first:** see the [Documentation handbook — Part 2](HANDBOOK.md#part-2--why-security-first) ([HTML](https://vaquarkhan.github.io/mcp-test-harness/guide/handbook.html#security-first)). Runtime enforce: [MCP-Bastion handbook](https://vaquarkhan.github.io/MCP-Bastion/guide/bible.html).

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
| `assert_egress_quarantined` | Social-engineering / synthetic-identity egress must error with quarantine deny |
| `assert_egress_allowed` | Benign egress controls must pass (false-positive guard) |
| `assert_covert_channel_neutralized` | **Known encodings only** (zero-width, homoglyph, whitespace) must not survive |
| `assert_general_exec_tools_absent` | Capability-reduction: shell/exec tools must not be exposed |
| `assert_agents_md_clean` | **Agent rules files** (`AGENTS.md`, `CLAUDE.md`, `.cursorrules`, …): fail on hidden Unicode (Tags-block / bidi / zero-width) |

Corpora: `PROMPT_INJECTION_PAYLOADS`, `PATH_TRAVERSAL_PAYLOADS`, `SECRET_LEAK_PATTERNS`, `SOCIAL_ENGINEERING_PAYLOADS`, `BENIGN_EGRESS_CONTROLS`, `COVERT_CHANNEL_PAYLOADS`, `AISI_MAINTAINER_PRESSURE_PAYLOAD`.

### Agent instruction files (`agents_md_scan.py`)

Research shows invisible Unicode (Tags block U+E0000–U+E007F, zero-width, bidi overrides) can smuggle instructions into files agents treat as authority (`AGENTS.md`, `CLAUDE.md`, `.cursorrules`, skills). Humans see benign text; models still tokenize the hidden stream.

**Defensive CI only** — detect and fail; do not generate smuggling payloads.

```bash
mcp-test scan-agents              # discover + scan under cwd
mcp-test scan-agents --json       # machine-readable findings
mcp-test scan-agents --fail-on critical
```

```python
from mcp_test_harness import assert_agents_md_clean, marker

@marker(tags=["security", "agents-md"])
async def test_agents_md_no_hidden_unicode():
    assert_agents_md_clean()  # auto-discovers AGENTS.md / CLAUDE.md / .cursorrules / …
```

Opt-in gate (disabled by default — **non-breaking**):

```yaml
# mcp-test.yaml
agents_md_gate:
  enabled: true
  fail_on: high          # critical | high | medium | low
  # paths: [AGENTS.md]   # optional; default discovers common names
  # strict: false        # also flag leading BOM
```

### Suite A honesty (semantic egress)

- **CI gate** asserts *enforcement* against a recorded-verdict / fixture server (deny code / quarantine substring), not live model prose.
- **`semantic_live`** / **`adaptive`** pytest markers are reserved for nightly detection-quality and adaptive-attack trend runs — they must not gate PRs.
- Covert-channel helpers prove **known-encoding capacity reduction**, not absence of every channel.
- The AISI maintainer-pressure fixture is a **visible skip** (issue-linked known-gap) until bastion Extension A lands — not a silent `xfail`.
- Out-of-band shell/Tor paths are **out of scope** here; `assert_general_exec_tools_absent` is the deterministic configuration control for that gap.

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

**Manifest / rug-pull gate** (opt-in supply-chain control at merge time):

```yaml
# mcp-test.yaml
manifest_gate:
  enabled: true
  path: __snapshots__/mcp_manifest.snap   # optional; this is the default
```

On connect, the harness snapshots capabilities + tools/resources/prompts (names, descriptions, schemas) and fails the run if the live surface differs from the sanctioned baseline. Approve intentional changes with:

```bash
mcp-test --update-snapshots
# or
mcp-test manifest update
mcp-test manifest check    # CI-friendly exit codes
mcp-test manifest show     # print normalized JSON
```

Unlike runtime scanners (current state only), this gate enforces a **baseline** you version in-repo.

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
from mcp_test_harness import (
    marker,
    run_security_payload_pack,
    assert_authorization_boundary,
    assert_egress_quarantined,
    assert_egress_allowed,
    assert_covert_channel_neutralized,
    assert_general_exec_tools_absent,
)

@marker(tags=["security", "smoke"])
async def test_chat_injection_blocked(mcp_server):
    await run_security_payload_pack(
        mcp_server, "chat",
        injection_argument="input",
        path_argument="path",
    )

@marker(tags=["security", "semantic-egress"])
async def test_egress_quarantine(mcp_server):
    # Recorded-verdict / fixture server in CI — not a live evaluator.
    await assert_egress_quarantined(mcp_server, "send_message")
    await assert_egress_allowed(mcp_server, "send_message")

@marker(tags=["security", "covert-channel"])
async def test_known_covert_encodings(mcp_server):
    await assert_covert_channel_neutralized(mcp_server, "send_message")

@marker(tags=["security", "capability-reduction"])
async def test_no_general_exec_tools(mcp_server):
    await assert_general_exec_tools_absent(mcp_server)

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
| Security smoke | Every PR | `mcp-test -m security` / `pytest -m security` |
| Full payload suite | Nightly / main | All security-tagged tests |
| Detection quality | Nightly (not gated) | `pytest -m semantic_live` |
| Adaptive trend | Nightly (not gated) | `pytest -m adaptive` |
| Config audit (optional) | PR | `npx @mcp-shark/mcp-shark scan --ci` — see [COMPARISON.md](COMPARISON.md) |

## Integration model

- Core assertions stay **deterministic and fast**.
- Heavy scanners (e.g. Presidio PII) → plugins or [MCP-Bastion](https://github.com/vaquarkhan/MCP-Bastion).
- Runtime protection → Bastion in production; harness **verifies** defenses in CI.

## EU AI Act and governance

Demo pack: `examples/feature-demo/eu-ai-act/` — auth boundaries, deterministic checks, report artifacts.

Test artifacts support compliance **evidence packages**; they supplement — not replace — legal and risk review. See [ENTERPRISE_GOVERNANCE.md](ENTERPRISE_GOVERNANCE.md).

## Roadmap (remaining)

- Suite B/C/D cyber extensions (attestation, provenance) — phased; keep gated path deterministic
- Optional toxic-flow heuristics when multiple tool sources are detected
- Deeper integration with external fuzz engines (delegate, not embed)
