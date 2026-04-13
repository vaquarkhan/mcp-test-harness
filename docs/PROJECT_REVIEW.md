# End-to-end project review (MCPLint)

Last refreshed: living document — re-run tests and CI after major changes.

## Executive summary

| Area | Assessment |
| ---- | ---------- |
| **Test suite** | **Strong** — 370 tests, broad coverage of harness modules (local run). |
| **Documentation** | **Strong** — README, DEVELOPER_GUIDE, TUTORIAL, DECISIONS. |
| **CI** | **Fixed** — Quick job now sets `PYTHONPATH`, installs `mcp` + harness deps without pulling MCP-Bastion/torch, runs all tests except `test_workspace.py`. Full job still validates Bastion + `mcp-test --version`. |
| **Packaging** | **Watch** — `mcp-bastion-python` as a **required** dependency forces a very large install for users who only want `mcp-test`; consider optional extra `[bastion]` (see below). |
| **License** | **Clarify** — Custom LICENSE (attribution + non-commercial). PyPI classifier says `Other/Proprietary`; ensure README/LICENSE match what you publish. |

---

## Strengths

1. **Clear product story** — MCP test harness (`mcp-test`) plus optional `mcplint` shim for ecosystem versions; README states this upfront.
2. **Large automated test matrix** — Config, parser, discovery, transport, plugins, executor, assertions, CLI, snapshots, etc.
3. **Split CI** — Fast PR path without GPU/ML stack; full path after merge with Bastion smoke (`verify_upstream.py`).
4. **Developer docs** — DEVELOPER_GUIDE and TUTORIAL support onboarding.
5. **Pinned action SHAs** — Supply-chain conscious GitHub Actions versions.

---

## Issues found and status

| Issue | Severity | Status / recommendation |
| ----- | -------- | ------------------------- |
| Quick CI did not set `PYTHONPATH` or install `mcp` — harness imports would fail on GitHub | **High** | **Fixed** in `validate.yml`: `PYTHONPATH=src`, `pip install mcp pyyaml jsonschema anyio pytest pytest-asyncio`. |
| Quick CI listed only a subset of test files — skipped `test_*_extra`, `test_*_gaps` | **Medium** | **Fixed**: `pytest tests/ --ignore=tests/test_workspace.py`. |
| `test_workspace.py` requires `mcp-bastion-python` on disk for `bastion_version()` | **Expected** | Run only in **full** job with `pip install -e ".[dev]"`. |
| Pytest warned on harness types named `Test*` | **Low** | **Fixed:** renamed to `HarnessCase`, `HarnessModule`, `CaseExecutor`, `HarnessScheduler`, `CaseStatus`, `CaseResult`, `SessionResults`. |
| `asyncio.get_event_loop()` in `test_assertions.py` | **Low** | **Fixed:** use `asyncio.run(...)`. |
| `mcp-bastion-python` required in `[project] dependencies` | **Medium** | **Optional:** move to extra `[bastion]` for lighter default installs. |
| License vs README vs PyPI | **Policy** | **Aligned:** README License section and `pyproject.toml` description reference custom non-commercial LICENSE and `Other/Proprietary` classifier. |

---

## Suggested next steps (optional)

1. Optional-ize `mcp-bastion-python` in `pyproject.toml` and document `pip install mcplint[bastion]`.
2. Run `pip-audit` / Dependabot on `pyproject.toml` for supply-chain visibility.
3. Address remaining `starlette` / `multipart` PendingDeprecationWarning from transitive deps (if it appears in your runs).

---

## How to re-validate locally

```bash
# Fast (no Bastion)
set PYTHONPATH=src   # Windows
export PYTHONPATH=src  # Unix
pip install mcp pyyaml jsonschema anyio pytest pytest-asyncio
pytest tests/ --ignore=tests/test_workspace.py -q

# Full
pip install -e ".[dev]"
pytest tests/ -q
python scripts/verify_upstream.py
mcp-test --version
```
