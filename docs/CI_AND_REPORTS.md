# CI, test reports, and “publishing” results

This page answers: **do you have to publish test reports?** and how that relates to MCP Test Harness and CI, in the same spirit as the operational docs in [MCP-Bastion](https://github.com/vaquarkhan/MCP-Bastion) (where CI, supply chain, and observability are first-class).

## Short answer

| Question | Answer |
|----------|--------|
| **Must we publish test reports to the public internet?** | **No.** For libraries and most apps, **failing the job on a non-zero exit code** is enough. |
| **Must we “publish” reports inside the org?** | **Optional.** Upload JUnit (or full logs) as **CI artifacts** for debugging and history. |
| **Is a public website of HTML test history required?** | **No** for PyPI or normal GitHub. **Only if** you want a browsable, static history (e.g. GitHub Pages for project docs; rare for a small CLI). |

## What the harness already gives you

- **Exit code:** `0` = all passed, non-zero = failures, errors, or config problems — suitable for any CI gate.
- **Console output:** Human-readable summary in the log (always).
- **Optional file outputs** (see [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) reporting section):
  - **JUnit XML** — ideal for **GitHub Actions** (`dorny/test-reporter`, annotations), Jenkins, GitLab.
  - **JSON** — machine-readable metadata, downstream tooling.
  - **HTML** — local or artifact-friendly report for humans.

## Recommended CI pattern (no public “site”)

1. Run `mcp-test` in GitHub Actions (or similar).
2. On failure, inspect the log; optionally attach:
   - `--report-format junit --report-output junit.xml`
   - `actions/upload-artifact` for `junit.xml` and/or HTML.

That is **not** “publishing” in the marketing sense; it is **retaining** build outputs for the team. No GitHub Pages required.

## When to publish / host reports publicly

- **Open-source project sites** that already use **GitHub Pages** for hand-written docs: you *may* add a “latest CI report” only if you intentionally build that pipeline (e.g. generate static HTML in CI, push to `gh-pages`). This is **extra maintenance** and is **unusual** for a small test runner project.
- **Internal**: use your org’s S3, Artifactory, or “artifacts only” in Actions — not public URLs.

## Summary

- **You do not need to publish test results** to users of your package.
- You **do** want **reliable CI** (exit code + log); **JUnit/JSON/HTML** are **optional** quality-of-life for humans and merge gates.
- For security-adjacent operations (audit, long-term evidence), the **harness** produces structured output; your **governance** decides where those files live — same idea as [MCP-Bastion’s](https://github.com/vaquarkhan/MCP-Bastion) supply-chain and observability docs, at a smaller scope for testing.
