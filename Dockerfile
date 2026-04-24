# syntax=docker/dockerfile:1
# OCI image for the mcp-test CLI. Default build is a small runtime; use --target dev to run tests in CI.
# Build:  docker build -t mcp-test-harness:local .
# Dev:    docker build -t mcp-test-harness:dev --target dev .

FROM python:3.12-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md LICENSE NOTICE CITATION.cff ./
COPY src ./src

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Optional: pytest, jsonschema, PyInstaller, etc. (same as pip install ".[dev]").
# Run tests: docker run --rm -v ${PWD}:/work -w /work --entrypoint pytest mcp-test-harness:dev tests/ -q
FROM base AS dev
RUN pip install --no-cache-dir ".[dev]"
ENTRYPOINT ["mcp-test"]
CMD ["--help"]

# Default image: mcp-test only (typical for mounting your repo and running the CLI).
FROM base AS runtime
ENTRYPOINT ["mcp-test"]
CMD ["--help"]
