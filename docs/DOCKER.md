# Docker and OCI images

MCP Test Harness ships a [Dockerfile](../Dockerfile) at the repository root. Use it to run **`mcp-test` in a reproducible, Python-isolated** environment (CI, air-gapped runners, or teams that standardize on containers instead of a local venv).

## Find images and packages

| What | Link |
|------|------|
| **PyPI (Python wheel + sdist)** | [https://pypi.org/project/mcp-test-harness/](https://pypi.org/project/mcp-test-harness/) |
| **This repo’s `Dockerfile` (source of truth)** | [Dockerfile in main](https://github.com/vaquarkhan/mcp-test-harness/blob/main/Dockerfile) |
| **GitHub** — source, Issues, **Packages** (if the project publishes a container) | [Repository](https://github.com/vaquarkhan/mcp-test-harness) · [org packages (vaquarkhan)](https://github.com/vaquarkhan?tab=packages) |
| **Docker product docs** (install, `docker run`, volume mounts) | [https://docs.docker.com/](https://docs.docker.com/) |

**Note:** Release automation in this repository currently publishes the **Python package to PyPI** (see [`.github/workflows/publish.yml`](../.github/workflows/publish.yml)). **Pre-built** `linux/amd64` (or multi-arch) images on **GitHub Container Registry** (`ghcr.io`) may be added later; when they exist, they will typically appear under the repo’s [Packages](https://github.com/vaquarkhan/mcp-test-harness) tab or the organization’s [packages](https://github.com/vaquarkhan?tab=packages). Until then, build any image you need locally (below).

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

## If you add GHCR (maintainers)

When publishing a container to **GitHub Container Registry**, a common tag shape is:

`ghcr.io/vaquarkhan/mcp-test-harness:<git-tag>`

For example, after implementing a `docker push` step in CI on `v*`, add that URL to the [Discovery checklist](DISCOVERY.md) and to the root [README](../README.md) next to the Docker section so users can **discover the image in one click**.

**Related:** [CHANGELOG](../CHANGELOG.md) (what changed in each release) · [Contributing / tests in Docker](../CONTRIBUTING.md).
