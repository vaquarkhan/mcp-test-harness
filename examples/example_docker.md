# Docker (OCI image with `mcp-test`)

**Build** (from repo root — same as [README #docker](../README.md#docker)):

```bash
docker build -t mcp-test-harness:local .
docker run --rm mcp-test-harness:local --version
```

**Run harness against a mounted project** (POSIX):

```bash
docker run --rm -v "$PWD":/work -w /work mcp-test-harness:local .
```

**Dev image (pytest in container):** `docker build -t mcp-test-harness:dev --target dev .` then override `--entrypoint pytest` to run the suite.

**Deeper** (registries, `ghcr.io`, diagram): [DOCKER.md](../docs/DOCKER.md)
