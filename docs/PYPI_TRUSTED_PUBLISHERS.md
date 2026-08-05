# PyPI Trusted Publishers (MCP Test Harness)

One-time setup at https://pypi.org/manage/account/publishing/

**Shared values for every harness provider shim:**

| Field | Value |
|-------|--------|
| Owner | `vaquarkhan` |
| Repository name | `mcp-test-harness` |
| Workflow name | `publish-packages.yml` |
| Environment name | `pypi` |

**Core package** (`mcp-test-harness`) uses workflow **`publish.yml`** (tag `v*`), same owner/repo/environment.

Publish a provider after adding the pending publisher:

```bash
gh workflow run publish-packages.yml -f package=mcp-test-harness-langgraph --ref main
```

---

## New packages (add as Pending publisher)

### `mcp-test-harness-langgraph`

| Field | Value |
|-------|--------|
| PyPI Project Name | `mcp-test-harness-langgraph` |
| Owner | `vaquarkhan` |
| Repository name | `mcp-test-harness` |
| Workflow name | `publish-packages.yml` |
| Environment name | `pypi` |

### `mcp-test-harness-pydantic-ai`

| Field | Value |
|-------|--------|
| PyPI Project Name | `mcp-test-harness-pydantic-ai` |
| Owner | `vaquarkhan` |
| Repository name | `mcp-test-harness` |
| Workflow name | `publish-packages.yml` |
| Environment name | `pypi` |

### `mcp-test-harness-openai-agents`

| Field | Value |
|-------|--------|
| PyPI Project Name | `mcp-test-harness-openai-agents` |
| Owner | `vaquarkhan` |
| Repository name | `mcp-test-harness` |
| Workflow name | `publish-packages.yml` |
| Environment name | `pypi` |

---

## Validate locally (adopter matrix)

```bash
python scripts/sync_provider_packages.py --version 4.0.1
python -m pytest tests/test_provider_package_helpers.py -q
```

CI: `.github/workflows/validate.yml` (Quick + dist-smoke provider imports).
