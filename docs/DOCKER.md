# Docker and OCI images

MCP Test Harness ships a [Dockerfile](../Dockerfile) at the repository root. Use it to run **`mcp-test` in a reproducible, Python-isolated** environment (CI, air-gapped runners, or teams that standardize on containers instead of a local venv).

## Find images and packages

| What | Link |
|------|------|
| **PyPI (Python wheel + sdist)** | [https://pypi.org/project/mcp-test-harness/](https://pypi.org/project/mcp-test-harness/) |
| **This repo’s `Dockerfile` (source of truth)** | [Dockerfile in main](https://github.com/vaquarkhan/mcp-test-harness/blob/main/Dockerfile) |
| **GitHub** — source, Issues, **Packages** (container images) | [Repository](https://github.com/vaquarkhan/mcp-test-harness) · [Packages for this repo](https://github.com/vaquarkhan/mcp-test-harness/pkgs/container/mcp-test-harness) · [org packages (vaquarkhan)](https://github.com/vaquarkhan?tab=packages) |
| **GHCR (pre-built images)** | `docker pull ghcr.io/vaquarkhan/mcp-test-harness:latest` — published on each **`v*`** tag by [`.github/workflows/docker-publish.yml`](../.github/workflows/docker-publish.yml) (see [RELEASING.md](RELEASING.md)). |
| **Docker product docs** (install, `docker run`, volume mounts) | [https://docs.docker.com/](https://docs.docker.com/) |

**Note:** Pushing a **`vX.Y.Z`** tag runs **PyPI** ([`publish.yml`](../.github/workflows/publish.yml)) and **GHCR** ([`docker-publish.yml`](../.github/workflows/docker-publish.yml)) in parallel. You can still **build locally** with the [Dockerfile](../Dockerfile) (below).

## Image targets (one Dockerfile, two use cases)

```mermaid
flowchart TB
  subgraph build["docker build from repo root"]
    DF["Dockerfile"]
  end
  DF --> B["base: mcp + harness wheel"]
  B --> R["default / runtime: ENTRYPOINT mcp-test"]
  B --> D["--target dev: + pytest, jsonschema, dev extras"]
```

| Target | `docker build` | Typical use |
|--------|----------------|-------------|
| **runtime** (default last stage) | `docker build -t mcp-test-harness:local .` | Smallest image: run `mcp-test` against a mounted project. |
| **dev** | `docker build -t mcp-test-harness:dev --target dev .` | Run `pytest` / coverage inside the container against a mounted tree. |

## Build and run locally

From the [repository root](https://github.com/vaquarkhan/mcp-test-harness):

```bash
docker build -t mcp-test-harness:local .
docker run --rm mcp-test-harness:local --version
```

Run the harness against the current directory (POSIX; see root [README](../README.md#docker) for PowerShell):

```bash
docker run --rm -v "$PWD":/work -w /work mcp-test-harness:local .
```

**Dev / tests:**

```bash
docker build -t mcp-test-harness:dev --target dev .
docker run --rm -v "$PWD":/work -w /work --entrypoint pytest mcp-test-harness:dev tests/ -q
```

## GHCR in CI (implemented)

On **`v*`** tags, [`.github/workflows/docker-publish.yml`](../.github/workflows/docker-publish.yml) pushes:

- **Runtime:** `ghcr.io/vaquarkhan/mcp-test-harness:<semver>` and `:latest`
- **Dev:** `ghcr.io/vaquarkhan/mcp-test-harness:<semver>-dev` and `:dev`

One-time GitHub **Actions** workflow permission **Read and write** is required so `GITHUB_TOKEN` can push packages. Maintainer checklist: [RELEASING.md](RELEASING.md).

**Related:** [CHANGELOG](../CHANGELOG.md) · [Contributing / tests in Docker](../CONTRIBUTING.md) · [Discovery checklist](DISCOVERY.md).
