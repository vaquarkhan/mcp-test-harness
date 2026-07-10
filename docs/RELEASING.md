# Releasing (PyPI + Docker / GHCR)

This repo publishes **two artifacts** from the same **Git tag** `vX.Y.Z`:

| Artifact | Trigger | Workflow |
|----------|---------|----------|
| **Python wheel + sdist** on **PyPI** | Push tag `v*` | [`.github/workflows/publish.yml`](../.github/workflows/publish.yml) |
| **OCI images** on **GHCR** (`ghcr.io`) | Push tag `v*` | [`.github/workflows/docker-publish.yml`](../.github/workflows/docker-publish.yml) |

## One-time setup (maintainers)

### PyPI (Trusted Publishing)

1. In **PyPI** → your project → **Publishing** → add a **pending** trusted publisher for **GitHub** (repo `vaquarkhan/mcp-test-harness`, workflow `publish.yml`, environment `pypi` — match your [PyPI docs](https://docs.pypi.org/trusted-publishers/)).
2. In **GitHub** → **Settings** → **Environments** → create **`pypi`** (optional protection rules / reviewers).
3. Ensure [`.github/workflows/publish.yml`](../.github/workflows/publish.yml) uses `permissions: id-token: write` and `environment: pypi` (already configured).

### GitHub Container Registry

1. **GitHub** → **Settings** → **Actions** → **General** → **Workflow permissions** → select **Read and write** (so `GITHUB_TOKEN` can push packages).
2. After the **first** `docker-publish` run, open the package under **Packages**, set **visibility** (public / internal) and link it to this repo if prompted.

## Release checklist (each version)

1. **Version** — bump in [pyproject.toml](../pyproject.toml), all **`packages/mcp-test-harness-*`** `pyproject.toml` + `__init__.py` files (18 artifacts total), [server.json](../server.json), [CITATION.cff](../CITATION.cff) (if you track version there), [html/](../html/) site badges, and [README.md](../README.md).
2. **Changelog** — add a dated section in [CHANGELOG.md](../CHANGELOG.md) for `X.Y.Z`.
3. **Commit** — merge to `main` (or your release branch).
4. **Tag and push** (from the commit you want to release):

   ```bash
   git tag v1.0.1
   git push origin v1.0.1
   ```

5. **Watch Actions** — [Actions](https://github.com/vaquarkhan/mcp-test-harness/actions): `publish` (main + **all 17 optional** wheels via matrix), `docker-publish` (GHCR `:X.Y.Z`, `:latest`, `:X.Y.Z-dev`, `:dev`) should succeed.

## Docker tags after a `v*` push (example: `v3.0.0`)

| Image | Tags (examples) |
|-------|-----------------|
| **Runtime** (default `mcp-test` entrypoint) | `ghcr.io/vaquarkhan/mcp-test-harness:3.0.0`, `:latest` |
| **Dev** (`pytest` / `[dev]` extras) | `ghcr.io/vaquarkhan/mcp-test-harness:3.0.0-dev`, `:dev` |

```bash
docker pull ghcr.io/vaquarkhan/mcp-test-harness:latest
docker run --rm ghcr.io/vaquarkhan/mcp-test-harness:latest --version
```

### Optional `packages/*` wheels (separate PyPI projects)

These use [`.github/workflows/publish-packages.yml`](../.github/workflows/publish-packages.yml), **not** the main `publish.yml`.

| Correct | Wrong |
|---------|--------|
| Tag **`pkg-mcp-test-harness-openai`** (directory under `packages/`) | Tag **`pkg-1.0.1`** → CI looks for `packages/1.0.1` and fails with *Source packages/1.0.1 is not a directory* |
| Or **Actions →** `publish-packages` → **Run workflow** → `package` = `mcp-test-harness-openai` | Using **`pkg-`** + semver — use **`v1.0.1`** for the **root** [pyproject.toml](../pyproject.toml) package only |

**Main package** → always **`vX.Y.Z`** (e.g. `v1.0.1`) → `publish.yml`.

## Related

- [DOCKER.md](DOCKER.md) — local build, targets, diagrams  
- [DISCOVERY.md](DISCOVERY.md) — PyPI + registry checklist  
- [CONTRIBUTING.md](../CONTRIBUTING.md) — dev tests before you tag  
