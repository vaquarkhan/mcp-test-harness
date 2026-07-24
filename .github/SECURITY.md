# Security Policy

Thank you for helping keep MCP Test Harness and downstream MCP deployments secure.

> **Important:** This policy is operational guidance for coordinated disclosure. It is not legal advice. CRA applicability depends on your product classification and role (manufacturer, importer, distributor, or open-source steward).

## Reporting a vulnerability

Please **do not** open a public GitHub Issue for security vulnerabilities.

Prefer one of:

1. **GitHub Security Advisories** — use [Report a vulnerability](https://github.com/vaquarkhan/mcp-test-harness/security/advisories/new) on this repository (private by default).
2. **Email** — contact the maintainers at `[SECURITY_CONTACT_EMAIL]` (replace with the published security contact).

Include as much detail as possible:

- Affected version / commit / package name (`mcp-test-harness` or a `mcp-test-harness-*` shim)
- Reproduction steps and expected vs actual behavior
- Impact assessment (confidentiality, integrity, availability)
- Whether you believe the issue is **actively exploited**

### Acknowledgement SLA

- We aim to **acknowledge** reports within **48 hours**.
- We will provide an initial severity triage and a remediation plan when feasible.
- Please allow reasonable time before public disclosure (coordinated disclosure).

## European Cyber Resilience Act (CRA) Compliance & Article 14 Reporting

Regulation **(EU) 2024/2847** (Cyber Resilience Act) introduces mandatory vulnerability handling and reporting obligations for Products with Digital Elements (PDEs), with Article 14 actively-exploited vulnerability reporting obligations phased in from **11 September 2026**.

For this repository:

- Maintainers will treat **critical** findings (for example CVSS ≥ 9.0, or clear remote exploitation of the harness against production MCP servers) as high priority.
- When a confirmed, **actively exploited** vulnerability in a released artifact may require notification under Article 14, maintainers will coordinate escalation toward the **ENISA Single Reporting Platform (SRP)** and/or the relevant national CSIRT **via the manufacturer/steward of the affected PDE** — the harness itself is typically a **CI tooling dependency**, not the end-user PDE.
- Downstream manufacturers using this harness to gate MCP servers remain responsible for their own CRA classification, CE marking, and ENISA reporting obligations.

Placeholders for operator configuration:

| Placeholder | Purpose |
|-------------|---------|
| `[SECURITY_CONTACT_EMAIL]` | Primary security contact |
| `[ENISA_SRP_PROCESS_OWNER]` | Person/team owning ENISA SRP submissions for *your* PDE |

## Supply chain transparency (SBOM)

Release pipelines for `v*` tags generate a **CycloneDX** Software Bill of Materials (`bom.json`) and upload it as a GitHub Actions artifact on:

- `.github/workflows/publish.yml` (PyPI wheel/sdist build)
- `.github/workflows/docker-publish.yml` (OCI images on GHCR)

Consumers should retain those artifacts with release records. See [docs/CRA_COMPLIANCE.md](../docs/CRA_COMPLIANCE.md).

## Supported versions

Security fixes are applied to the latest published major/minor line on PyPI. Older versions may not receive backports.

## Safe harbor

We will not pursue legal action against researchers who:

- Make a good-faith effort to avoid privacy violations, data destruction, and service disruption
- Report findings privately and give us a reasonable chance to remediate before disclosure
