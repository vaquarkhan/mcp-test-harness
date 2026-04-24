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

1. **Version** — bump in [pyproject.toml](../pyproject.toml), [server.json](../server.json), [CITATION.cff](../CITATION.cff) (if you track version there), and any **optional** `packages/mcp-test-harness-*` that ship with the same tag.
2. **Changelog** — add a dated section in [CHANGELOG.md](../CHANGELOG.md) for `X.Y.Z`.
3. **Commit** — merge to `main` (or your release branch).
4. **Tag and push** (from the commit you want to release):

   ```bash
   git tag v1.0.1
   git push origin v1.0.1
   ```

5. **Watch Actions** — [Actions](https://github.com/vaquarkhan/mcp-test-harness/actions): `publish` (PyPI) and `docker-publish` (GHCR) should both succeed.

## Docker tags after a `v1.0.1` push

| Image | Tags (examples) |
|-------|-----------------|
| **Runtime** (default `mcp-test` entrypoint) | `ghcr.io/vaquarkhan/mcp-test-harness:1.0.1`, `:latest` |
| **Dev** (`pytest` / `[dev]` extras) | `ghcr.io/vaquarkhan/mcp-test-harness:1.0.1-dev`, `:dev` |

```bash
docker pull ghcr.io/vaquarkhan/mcp-test-harness:latest
docker run --rm ghcr.io/vaquarkhan/mcp-test-harness:latest --version
```

**Optional packages** under `packages/` use [`.github/workflows/publish-packages.yml`](../.github/workflows/publish-packages.yml) with tags `pkg-<directory-name>` or **workflow_dispatch**.

## Related

- [DOCKER.md](DOCKER.md) — local build, targets, diagrams  
- [DISCOVERY.md](DISCOVERY.md) — PyPI + registry checklist  
- [CONTRIBUTING.md](../CONTRIBUTING.md) — dev tests before you tag  
