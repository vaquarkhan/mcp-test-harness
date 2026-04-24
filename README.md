<p align="center">
  <img src="docs/images/testherness.png" alt="MCP Test Harness" width="100%" />
</p>

# MCP Test Harness

[![PyPI version](https://img.shields.io/pypi/v/mcp-test-harness)](https://pypi.org/project/mcp-test-harness/)
[![PyPI downloads](https://img.shields.io/pypi/dm/mcp-test-harness)](https://pypi.org/project/mcp-test-harness/)
[![Python](https://img.shields.io/pypi/pyversions/mcp-test-harness)](https://pypi.org/project/mcp-test-harness/)
[![CI](https://img.shields.io/github/actions/workflow/status/vaquarkhan/mcp-test-harness/validate.yml?branch=main&label=CI)](https://github.com/vaquarkhan/mcp-test-harness/actions/workflows/validate.yml)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen)]()
[![Coverage](https://img.shields.io/badge/coverage-100%25%20%28lib%29-brightgreen)]()

**Automated Testing Framework for Model Context Protocol (MCP) Servers**

> **Documentation:** structured **hub** and **adoption paths** (same pattern as [MCP-Bastion](https://github.com/vaquarkhan/MCP-Bastion)) are in [docs/README.md](docs/README.md) — start there for [QUICK_START](docs/QUICK_START.md), the full [DEVELOPER_GUIDE](docs/DEVELOPER_GUIDE.md), [CI & reports](docs/CI_AND_REPORTS.md), **[performance / latency tests](docs/PERFORMANCE.md)**, **[how we compare to other MCP tools](docs/COMPARISON.md)**, **[ecosystem / registry discovery (release checklist)](docs/DISCOVERY.md)**, and **[CHANGELOG](CHANGELOG.md)** / **[CONTRIBUTING](CONTRIBUTING.md)**. **Community:** open an **Issue** for bugs, a **PR** for docs and examples.

Author: [Vaquar Khan](https://github.com/vaquarkhan)

MCP Test Harness is a pytest-style testing framework for [MCP](https://modelcontextprotocol.io/) servers. It provides the `mcp-test` CLI to discover, run, and report on tests automatically—replacing manual validation through the MCP Inspector.

**License:** the core project is under the [MIT License](LICENSE); see [NOTICE](NOTICE). [CITATION.cff](CITATION.cff) suggests how to cite the software in papers (optional, not a license condition). *(Optional packages under `packages/` may list their own terms in each package’s `pyproject.toml`.)*

For **CI-native, code-first** MCP test automation, MCP Test Harness **fills** that gap. For **spec conformance**, **LLM-in-the-loop** evals, and **model benchmarks**, other tools exist; see [docs/COMPARISON.md](docs/COMPARISON.md).

## Documentation

**Hub (table of all guides + suggested reading order):** [docs/README.md](docs/README.md)

| Document | Contents |
|----------|----------|
| [docs/QUICK_START.md](docs/QUICK_START.md) | **Fastest path** — install, `mcp-test init`, run |
| [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) | **Canonical reference** — setup, config, stdio/parallel/validation, assertions, reporting |
| [docs/CI_AND_REPORTS.md](docs/CI_AND_REPORTS.md) | **CI, JUnit, JSON, HTML** — do you need to *publish* test reports? (usually: no) |
| [docs/TUTORIAL.md](docs/TUTORIAL.md) | Step-by-step tutorial |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Architecture and product decisions |
| [docs/IMPLEMENTATION_CHECKLIST.md](docs/IMPLEMENTATION_CHECKLIST.md) | Maintainer: features vs. code locations |
| [docs/COMPARISON.md](docs/COMPARISON.md) | **Ecosystem** — Conformance, mcp-eval, MCPMark, testmcpy; when to use Harness + Bastion |
| [docs/LLM_TEST_GENERATION.md](docs/LLM_TEST_GENERATION.md) | **LLM + tests** — draft-with-review: good; **auto** trusted in CI: bad fit for this harness |
| [docs/COLLECTIONS.md](docs/COLLECTIONS.md) | **Postman / Newman–style** multi-step flows, “environments”, and roadmap (declarative collections not in core yet) |
| [docs/DISCOVERY.md](docs/DISCOVERY.md) | **Registries and promotion** — internal checklist (PyPI, [server.json](server.json), awesome lists) |
| [docs/DOCKER.md](docs/DOCKER.md) | **Docker & OCI** — PyPI, **GHCR** / **GitHub Packages** links, build targets, `docker run` |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | **Mermaid** diagrams: CLI → scheduler → lifecycle → session → tests |
| [docs/EDITORS.md](docs/EDITORS.md) | **Visual Studio Code & Cursor** — snippets, Mermaid preview, recommended extensions |
| [docs/MARKDOWN_CONVENTIONS.md](docs/MARKDOWN_CONVENTIONS.md) | **Markdown** — `[!TIP]` / `**Feature**` callouts and fenced code for readable docs |
| [CHANGELOG.md](CHANGELOG.md) | **Release history** (Keep a Changelog) |
| [CONTRIBUTING.md](CONTRIBUTING.md) | **How to contribute** (tests, coverage, release bumps) |
| [CITATION.cff](CITATION.cff) | **Optional citation** — machine-readable metadata (not required by the license) |
| [Dockerfile](Dockerfile) (and [`.dockerignore`](.dockerignore)) | **Container image** for `mcp-test` — see [Docker](#docker) |

For production security (prompt injection defense, PII redaction, rate limiting, RBAC), see [MCP-Bastion](https://github.com/vaquarkhan/MCP-Bastion) — the companion **security** middleware; this repo is for **test automation**.

## Core Features

| Feature | Description |
|---------|-------------|
| Test discovery | Finds `test_*.py` files and `test_` functions automatically (pytest conventions); broken files log a warning with path and exception |
| MCP assertions | `assert_tool_call`, `assert_resource_read`, `assert_prompt`, `assert_capabilities`, `assert_snapshot`, plus `assert_tool_schema`, `assert_protocol_version`, `assert_tool_idempotent`, **`assert_latency`** (single-call or **p95/p99/mean** over N runs + **warmup**) — see [docs/PERFORMANCE.md](docs/PERFORMANCE.md) |
| Fixture system | Built-in `mcp_server` / `mcp_server_session`, custom fixtures; **cycle detection** for dependency errors |
| Schema validation | JSON-RPC envelope checks; with `schema_validation: true` (default), post-connect checks on `initialize`, `tools/list` (+ tool `inputSchema`), `resources` / `prompts` list shapes, and a best-effort `call_tool` probe to validate `content` item shapes |
| Snapshot testing | Compare responses; `ignore_fields` and `mask_patterns` for unstable data |
| Parallel execution | Multiple workers; **tests from the same file stay on one worker** so per-module fixtures remain correct |
| Watch mode | `mcp-test --watch` re-runs when test `*.py` files change (configurable poll interval; debounce coalesces rapid saves) |
| Markers | `@marker(timeout=60, retry=3, tags=["smoke"])` and `@skip(reason="...")` |
| Reports | Console summary, JUnit XML (GitHub Actions/Jenkins/GitLab), JSON with full metadata |
| Plugin system | Extend with custom assertions, fixtures, reporters, and transport adapters |
| Transport support | stdio, SSE, streamable HTTP -- test local and remote servers |
| GitHub Action | One-line CI integration with artifact upload |
| **Docker** | [`Dockerfile`](Dockerfile) — OCI image with `mcp-test` (runtime) or `pytest` + dev extras via `--target dev` (see [Docker](#docker)) |
| Standalone binary | Single binary via PyInstaller, no Python required on target |

## Why MCP Test Harness (vs MCP Inspector)

| | MCP Inspector | MCP Test Harness |
|---|---|---|
| Execution | Manual, browser-based clicking | Automated CLI, runs in CI |
| CI/CD integration | Not possible | Native (exit codes, JUnit XML, GitHub Action) |
| Regression detection | Manual re-testing | Snapshot testing, automated on every commit |
| Schema validation | Manual visual check | Automatic on every response |
| Parallel testing | No | Yes, with per-worker server isolation |
| Reporting | Visual only | Console, JSON, JUnit XML |
| Extensibility | None | Plugin system for custom rules |

## Ecosystem (Conformance, evals, benchmarks)

MCP Test Harness is **deterministic** (your tests call the protocol directly; no LLM required). The wider MCP space includes **protocol conformance** suites, **agent/LLM** evaluation frameworks, and **model** benchmarks. A concise map of tools, when to use each, and how they **complement** (not replace) the harness is in **[docs/COMPARISON.md](docs/COMPARISON.md)**.

## Installation

Core harness (lightweight: `mcp` + YAML + anyio; **no** MCP-Bastion / Presidio stack):

```bash
pip install mcp-test-harness
```

**Optional** [mcplint](src/mcplint/) / MCP-Bastion pin helpers (transitive set can be **large**; same as a full Bastion install):

```bash
pip install mcp-test-harness[mcplint]
# or the historical PyPI name for the monorepo shim:
pip install mcplint
```

Or from source:

```bash
git clone https://github.com/vaquarkhan/mcp-test-harness.git
cd mcp-test-harness
python -m venv .venv && source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"
mcp-test --version
```

### Docker

**One-page guide (PyPI, container registries, Mermaid build diagram, `docker run` copy-paste):** [docs/DOCKER.md](docs/DOCKER.md) · **System diagram (flow + sequence):** [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · **Visual Studio Code & Cursor (snippets, Mermaid, extensions):** [docs/EDITORS.md](docs/EDITORS.md)

Pre-built **runtime** and **dev** (test tooling) images are defined in the repo [`Dockerfile`](Dockerfile) (and [`.dockerignore`](.dockerignore) keeps the build context small). **Pre-built** images on **GitHub Container Registry** (`ghcr.io`) are not guaranteed until a release workflow publishes them; see [docs/DOCKER.md](docs/DOCKER.md) for the canonical **image / package** links and how to find **GitHub Packages** for this org.

| Build | Description |
|-------|-------------|
| **Default (runtime)** | `mcp-test` and core dependencies only — smallest image. |
| **`--target dev`** | Adds the same optional packages as `pip install -e ".[dev]"` (e.g. **pytest**, **jsonschema**, **PyInstaller**). Use this when you want to run the project’s `tests/` inside a container. |

**Build the default image** (from the repository root; requires [Docker](https://docs.docker.com/get-docker/)):

```bash
docker build -t mcp-test-harness:local .
```

**Smoke the CLI** (the image entrypoint is `mcp-test`):

```bash
docker run --rm mcp-test-harness:local --version
```

**Run `mcp-test` against a project** mounted into the working directory (paths below use POSIX shells; on Windows, use PowerShell and replace `$PWD` with your project path, e.g. ``${PWD}`` in Git Bash, or the full `C:\...` form):

```bash
docker run --rm -v "$PWD":/work -w /work mcp-test-harness:local
```

The default command shows `mcp-test --help`. Pass the same arguments you use locally, for example `docker run --rm -v "$PWD":/work -w /work mcp-test-harness:local .` to discover and run tests in the current config.

**Build the dev image and run the test suite** (requires your test tree mounted into `/work`):

```bash
docker build -t mcp-test-harness:dev --target dev .
docker run --rm -v "$PWD":/work -w /work --entrypoint pytest mcp-test-harness:dev tests/ -q
```

For coverage as in [pyproject.toml](pyproject.toml), you can add `--cov=src/mcp_test_harness` if your `tests/` and config are on the mount.

**Windows (PowerShell)**, using Docker Desktop, mount the current directory, for example:

```powershell
docker run --rm -v "${PWD}:/work" -w /work mcp-test-harness:local
```

**Size and first-build time** depend on what you install: the default **runtime** image matches `mcp-bastion-python`-free core dependencies. If you add **`[dev]`**, **`[mcplint]`**, or `pip install mcp-bastion-python` in the same environment, the resolver may pull a **large** transitive set (e.g. Presidio / NLP and, on many Linux x86_64 wheels, very large ML/CUDA-related packages). The first `docker build` with those extras can take a long time and produce a **multi-gigabyte** image. That is expected for a full install of the Bastion tree, not a bug in the `Dockerfile` when you opt into that stack.

> **Note:** The Docker image is optional; many teams use `pip install` in CI. Use the image when you need a **reproducible, Python-isolated** environment without a local venv, or a **portable** `mcp-test` in pipelines that standardize on containers.

## Quick Start

### 0. Scaffold a starter (optional)

With `mcp-test` on your `PATH` (after `pip install`):

```bash
mcp-test init
```

This writes `tests/test_mcp_server_example.py` and a minimal `mcp-test.yaml`. Set your real launch command, for example:

```bash
mcp-test init --server-command "python -m your_package.mcp"
```

Options: `mcp-test init --help` (custom `--dir`, `--filename`, `--no-config`, `--force`).

**Editor snippets:** the repo includes [`.vscode/mcp-test-harness.code-snippets`](.vscode/mcp-test-harness.code-snippets) — in VS Code or Cursor, type prefixes like `mcp-assert-tool` or `mcp-test-async` in a `*.py` file to insert common patterns.

### 1. Write a test

Create `tests/test_my_server.py`:

```python
from mcp_test_harness import assert_tool_call, assert_capabilities

async def test_server_has_tools(mcp_server):
    """Verify the server advertises tool capabilities."""
    await assert_capabilities(mcp_server, {"tools": {}})

async def test_echo_tool(mcp_server):
    """Call the echo tool and check it works."""
    result = await assert_tool_call(mcp_server, "echo", {"message": "hello"})
    assert result is not None
```

The `mcp_server` parameter is a built-in fixture. The harness automatically starts your server, connects via MCP, performs the initialize handshake, and injects a ready-to-use session.

### 2. Run it

```bash
mcp-test --server-command "python my_server.py" tests/
```

Output:

```
  [PASS] test_server_has_tools (45.2ms)
  [PASS] test_echo_tool (120.8ms)

2 passed, 0 failed, 0 errored, 0 skipped
Total time: 312.5ms
```

### 3. Add a config file

Create `mcp-test.yaml`:

```yaml
server:
  command: python my_server.py
  transport: stdio

test:
  dirs: [tests/]
  timeout: 30

report:
  format: junit
  output: reports/results.xml
```

Then just: `mcp-test`

## Assertion Reference

### assert_tool_call -- invoke a tool and validate the response

```python
# Basic: fail if the tool returns an error
await assert_tool_call(mcp_server, "echo", {"message": "hello"})

# With expected output
await assert_tool_call(mcp_server, "add", {"a": 1, "b": 2},
    expected=[{"text": "3", "isError": False}])

# Validate arguments against the tool’s inputSchema (requires `jsonschema`)
await assert_tool_call(
    mcp_server, "add", {"a": 1, "b": 2},
    validate_against_input_schema=True,
)

# Use the return value
result = await assert_tool_call(mcp_server, "get_data", {})
assert len(result.content) > 0
```

Other helpers: `assert_tool_schema`, `assert_protocol_version`, `assert_tool_idempotent`, `assert_latency`, `assert_tool_call_validates_input` — see **Part 3b** in the [Developer Guide](docs/DEVELOPER_GUIDE.md).

### assert_resource_read -- read a resource and check content/MIME type

```python
await assert_resource_read(mcp_server, "file:///config.json",
    expected_content='{"debug": true}',
    expected_mime_type="application/json")
```

### assert_prompt -- get a prompt and validate messages

```python
await assert_prompt(mcp_server, "summarize",
    arguments={"text": "The quick brown fox."},
    expected_messages=[{"role": "assistant", "content": "Summary: A fox."}])
```

### assert_capabilities -- verify server capabilities

```python
await assert_capabilities(mcp_server, {"tools": {}, "resources": {}})
```

### assert_snapshot -- regression detection via stored snapshots

```python
from pathlib import Path
from mcp_test_harness import assert_snapshot

async def test_stable_output(mcp_server):
    result = await mcp_server.call_tool("generate_report", {})
    await assert_snapshot(result, "report_output", test_file=Path(__file__))

# Drop volatile fields or mask dynamic strings (regex patterns)
async def test_noisy_output(mcp_server):
    result = await mcp_server.call_tool("with_ids", {})
    await assert_snapshot(
        result,
        "noisy",
        test_file=Path(__file__),
        ignore_fields=["requestId", "timestamp"],
        mask_patterns=[r"req_[a-f0-9]+"],
    )
```

First run creates the snapshot. Later runs compare against it. Update with `mcp-test --update-snapshots`.

All assertions produce diff output on failure:

```
  [FAIL] test_echo (18.5ms)
      Tool 'echo' response mismatch
      --- expected
      +++ actual
      @@ -1,3 +1,3 @@
       [
      -  {"text": "hello", "isError": false}
      +  {"text": "HELLO", "isError": false}
       ]
```

## Fixtures

Built-in fixtures:

| Fixture | Scope | Description |
|---------|-------|-------------|
| `mcp_server` | Per-test | Fresh MCP session for each test |
| `mcp_server_session` | Per-module | Shared session across all tests in a file |

Custom fixtures:

```python
from mcp_test_harness.fixtures import fixture, FixtureScope

@fixture
async def api_key():
    return "test-key-12345"

@fixture
async def database():
    db = await connect()
    yield db              # test runs here
    await db.close()      # teardown

@fixture(scope=FixtureScope.PER_MODULE)
async def shared_client():
    client = await create_client()
    yield client
    await client.close()

# Injected by parameter name
async def test_query(mcp_server, database, api_key):
    result = await mcp_server.call_tool("query", {"db": database.url, "key": api_key})
```

## Markers

```python
from mcp_test_harness import marker, skip

@marker(timeout=120)                    # custom timeout
@marker(retry=3)                        # retry on failure
@marker(tags=["smoke", "critical"])     # tags for filtering
@marker(timeout=60, retry=2, tags=["integration"])  # combine

@skip                                   # skip unconditionally
@skip(reason="Bug #42")                # skip with reason
```

Filter from CLI:

```bash
mcp-test -m smoke           # run only smoke-tagged tests
mcp-test -k "test_echo"     # run tests matching name
mcp-test -k "*workflow*"    # glob patterns
```

## Reports

```bash
# JUnit XML for CI (GitHub Actions, Jenkins, GitLab)
mcp-test --report-format junit --report-output results.xml

# JSON with full metadata (server capabilities, retry history, schema violations)
mcp-test --report-format json --report-output results.json
```

Console output is always printed:

```
  [PASS] test_echo (45.2ms)
  [FAIL] test_divide (18.5ms)
      Division by zero
  [SKIP] test_future (0.0ms)

2 passed, 1 failed, 0 errored, 1 skipped
Total time: 200.0ms
```

## Parallel Execution

```bash
mcp-test --parallel              # use all CPU cores
mcp-test --parallel --workers 4  # specify worker count
```

Each worker gets its own server instance. If one crashes, others continue.

**Module grouping:** tests from the same file are always scheduled on the **same** worker, so per-module fixtures (`mcp_server_session`, etc.) stay valid. Do not rely on test order *across* different files in parallel mode.

## Transport Support

| Transport | Use case | Example |
|-----------|----------|---------|
| stdio | Local servers (default) | `--server-command "python server.py"` |
| SSE | Remote servers via Server-Sent Events | `--transport sse --server-command "http://localhost:8080/sse"` |
| HTTP | Remote servers via streamable HTTP | `--transport http --server-command "http://localhost:8080/mcp"` |

With authentication:

```yaml
server:
  command: http://your-server.example.com/mcp
  transport: http
  transport_options:
    headers:
      Authorization: "Bearer your-token"
```

## GitHub Action

```yaml
# .github/workflows/mcp-tests.yml
name: MCP Server Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Test MCP Server
        uses: vaquarkhan/mcp-test-harness/.github/actions/mcp-test@main
        with:
          server-command: "python my_server.py"
          test-directory: "tests/"
          report-format: "junit"
```

| Input | Default | Description |
|-------|---------|-------------|
| `server-command` | `""` | Command to start the server |
| `transport` | `stdio` | stdio, sse, or http |
| `test-directory` | `tests/` | Path to test files |
| `config-file` | `""` | Path to config file |
| `report-format` | `junit` | json or junit |
| `harness-version` | `latest` | Version to install |

## Plugins

Extend MCP Test Harness with custom assertions, fixtures, reporters, and transports:

```python
from mcp_test_harness.plugins import PluginContext
from mcp_test_harness.fixtures import FixtureScope

class MyPlugin:
    name = "my-plugin"

    def register(self, context: PluginContext) -> None:
        context.add_assertion("assert_latency", check_latency)
        context.add_fixture("db", db_factory, FixtureScope.PER_MODULE)
        context.add_reporter("markdown", MarkdownReporter())

plugin = MyPlugin()
```

Load via config:

```yaml
plugins:
  - my_plugin.py
  - my_package.plugin_module
```

Or via Python entry points (auto-discovered):

```toml
[project.entry-points.mcp_test_harness]
my-plugin = "my_package.plugin:plugin"
```

See [examples/reference_plugin.py](examples/reference_plugin.py) for a complete example.

**More examples and patterns:** [examples/README.md](examples/README.md) and the **per-feature checklist** [examples/FEATURES_INDEX.md](examples/FEATURES_INDEX.md) (assertions demo, config validation, reports, transports, GitHub Action, Docker, watch mode, …). Copy-paste tests: [patterns_mcp_test.md](examples/patterns_mcp_test.md). For working on the harness source tree, use [docs/DEVELOPER.md](docs/DEVELOPER.md).

## Standalone Binary

```bash
pip install -e ".[dev]"
python scripts/build_binary.py
dist/mcp-test --version
```

No Python required on the target machine. Cross-platform: Linux, macOS, Windows.

## Security Testing with MCP-Bastion

MCP Test Harness tests that your MCP server works correctly. For production security, pair it with [MCP-Bastion](https://github.com/vaquarkhan/MCP-Bastion) -- an active defense middleware that protects MCP servers at runtime.

| Concern | Tool | What it does |
|---------|------|-------------|
| Functional testing | **MCP Test Harness** | Automated tests for tools, resources, prompts, capabilities |
| Prompt injection defense | [MCP-Bastion](https://github.com/vaquarkhan/MCP-Bastion) | Blocks jailbreaks via Meta PromptGuard (local, under 5ms) |
| PII redaction | [MCP-Bastion](https://github.com/vaquarkhan/MCP-Bastion) | Masks SSN, email, phone via Microsoft Presidio |
| Rate limiting | [MCP-Bastion](https://github.com/vaquarkhan/MCP-Bastion) | Token budgets, iteration caps, denial-of-wallet protection |
| RBAC | [MCP-Bastion](https://github.com/vaquarkhan/MCP-Bastion) | Tool-level permissions by role |
| Schema validation | **MCP Test Harness** | Validates JSON-RPC responses against MCP spec |
| Regression detection | **MCP Test Harness** | Snapshot testing catches unintended changes |
| Audit logging | [MCP-Bastion](https://github.com/vaquarkhan/MCP-Bastion) | Logs who, what, when, blocked/allowed |

Use both together for a complete MCP server development workflow:

```bash
# Test your server
mcp-test --server-command "python my_server.py" tests/

# Secure your server
pip install mcp-bastion-python
```

```python
# In your server code
from mcp_bastion import MCPBastionMiddleware

bastion = MCPBastionMiddleware(
    enable_prompt_guard=True,
    enable_pii_redaction=True,
    enable_rate_limit=True,
)
```

MCP-Bastion supports 16+ framework integrations including FastMCP, LangChain, OpenAI, Anthropic, AWS Bedrock, and more. See the [MCP-Bastion README](https://github.com/vaquarkhan/MCP-Bastion) for full docs.

## Dependency Management (mcplint shim)

The `mcplint` sub-package pins MCP-Bastion versions and provides helpers:

```python
from mcplint import bastion_version, bedrock_version

print(bastion_version())    # e.g. "1.0.12"
print(bedrock_version())    # None if bedrock extra not installed
```

Verify: `python scripts/verify_upstream.py`

## CLI Reference

```
mcp-test [TEST_PATH] [OPTIONS]

  --server-command CMD     Command to start the MCP server
  --transport TYPE         stdio | sse | http (default: stdio)
  --config PATH            Path to mcp-test.yaml or mcp-test.toml
  --timeout SECONDS        Per-test timeout (default: 30)
  --parallel               Run tests in parallel
  --workers N              Parallel worker count (default: CPU count)
  -k PATTERN               Filter by test name
  -m MARKER                Filter by marker/tag
  --list                   List tests and exit
  --watch                  Re-run on test file changes (poll + debounce via env; not with --list)
  --report-format FORMAT   json | junit | html
  --report-output PATH     Report file path
  --verbose                Full server communication logs
  --update-snapshots       Overwrite stored snapshots
  --version                Print version
```

Exit codes: `0` = passed, `1` = failures, `2` = config error

## Configuration Reference

```yaml
server:
  command: python my_server.py       # required
  transport: stdio                   # stdio | sse | http
  transport_options: {}              # host, port, headers, etc.

test:
  dirs: [tests/]                     # directories to search
  timeout: 30                        # per-test timeout (seconds)
  parallel: false                    # run in parallel
  workers: 4                         # parallel worker count

report:
  format: junit                      # json | junit
  output: reports/results.xml        # output file path

schema_validation: true              # validate JSON-RPC responses; parallel: only worker 0 runs full checks unless true
validate_schema_each_parallel_worker: false  # set true to run post-connect schema on every worker
schema_probe_call_tool: true         # best-effort call first tool with {} to validate result content
plugins: []                          # plugin paths or module names
redact_patterns: []                  # regex patterns to redact from verbose output
```

## Project Structure

```
mcp-test-harness/
+-- pyproject.toml
+-- CHANGELOG.md                    # version history (Keep a Changelog)
+-- CONTRIBUTING.md                 # how to contribute; links docs hub + tests
+-- server.json                     # MCP registry / tooling metadata (bump with releases)
+-- mcp_test_harness.spec           # PyInstaller config
+-- src/
|   +-- mcplint/                    # dependency shim
|   +-- mcp_test_harness/           # test framework (14 modules)
|       +-- cli.py                  # mcp-test entry point
|       +-- config.py               # YAML/TOML config loading
|       +-- discovery.py            # test file/function discovery
|       +-- executor.py             # test execution, timeout, retry
|       +-- scheduler.py            # sequential + parallel scheduling
|       +-- lifecycle.py            # server start/stop/monitor
|       +-- transport.py            # stdio, SSE, HTTP adapters
|       +-- stdio_mcp.py            # stdio client + process handle
|       +-- assertions.py           # MCP assertion helpers
|       +-- schema.py               # JSON-RPC / MCP schema validation
|       +-- fixtures.py             # fixture manager
|       +-- plugins.py              # plugin registry
|       +-- reporting.py            # console, JSON, JUnit reporters
|       +-- snapshots.py            # snapshot testing
|       +-- parser.py               # JSON-RPC message parser
|       +-- models.py               # shared data models
+-- examples/
|   +-- README.md                  # catalog + per-feature table
|   +-- FEATURES_INDEX.md         # 1:1 map: README core feature -> example
|   +-- example_*.md              # one feature per file (transports, reports, watch, …)
|   +-- mcp_test_*.yaml            # report + transport copy-paste configs
|   +-- basic_usage.py
|   +-- version_gate.py
|   +-- reference_plugin.py         # complete plugin example
|   +-- assertions_async_demo.py    # assert_* with a fake session
|   +-- validate_mcp_test_config.py # YAML/TOML schema check
|   +-- sample_mcp_test.yaml
|   +-- patterns_mcp_test.md        # copy-paste yaml, markers, snapshots
+-- scripts/
|   +-- verify_upstream.py
|   +-- build_binary.py
+-- tests/                          # 500+ tests; 100% line gate on mcp_test_harness except stdio_mcp (see [docs/DEVELOPER.md](docs/DEVELOPER.md#stdio_mcp-and-the-coverage-gate))
+-- docs/
|   +-- README.md                   # documentation hub
|   +-- index.md                    # short landing (e.g. GitHub Pages)
|   +-- DISCOVERY.md                # registries / release promotion checklist
|   +-- DEVELOPER_GUIDE.md          # complete API and integration guide
|   +-- TUTORIAL.md                 # step-by-step tutorial
|   +-- DECISIONS.md                # architecture decisions
+-- .github/
    +-- actions/mcp-test/           # reusable GitHub Action
    +-- workflows/validate.yml      # CI pipeline
```

## Testing

```bash
# Run all MCP Test Harness tests (pythonpath=src is set in pyproject.toml for pytest)
python -m pytest tests/ -q

# Quick offline check (no heavy deps)
python -m pytest tests/test_pyproject.py -q

# With coverage
python -m coverage run -m pytest tests/ -q
python -m coverage report --show-missing
```

The repo enforces **100%** line coverage on `src/mcp_test_harness` **except** [`stdio_mcp.py`](src/mcp_test_harness/stdio_mcp.py), which is **omitted** from the gate in [`pyproject.toml`](pyproject.toml) (intentional: subprocess/stdio I/O; see [docs/DEVELOPER.md](docs/DEVELOPER.md#stdio_mcp-and-the-coverage-gate)). That is **not** a quality gap for the rest of the tree.

If imports resolve to a different installed copy of the package, run from the repo root so `src/` is used, or: `pip install -e ".[dev]"`.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `mcp-test: command not found` | Run `pip install -e ".[dev]"` |
| Tests hang | Check `--timeout`; server may not respond to MCP handshake |
| `No tests discovered` | Files must match `test_*.py` or `*_test.py`; functions must start with `test_`. Check logs: a **warning** is emitted if a test file fails to import |
| Snapshot mismatch | Run `mcp-test --update-snapshots` after intentional changes |
| Server crashes during tests | Check server logs; harness marks remaining tests as errored |
| Config file not found | Harness looks for `mcp-test.yaml` / `mcp-test.toml` in cwd, or use `--config` |

## Framework Integration Packages

MCP Test Harness provides framework-specific testing helpers. Each package auto-installs `mcp-test-harness` as a dependency:

| Package | Tests for | Version | Downloads |
|---------|-----------|---------|-----------|
| `mcp-test-harness` | Any MCP server (core) | [![PyPI](https://img.shields.io/pypi/v/mcp-test-harness)](https://pypi.org/project/mcp-test-harness/) | [![Downloads](https://img.shields.io/pypi/dm/mcp-test-harness)](https://pypi.org/project/mcp-test-harness/) |
| `mcp-test-harness-fastmcp` | FastMCP servers | [![PyPI](https://img.shields.io/pypi/v/mcp-test-harness-fastmcp)](https://pypi.org/project/mcp-test-harness-fastmcp/) | [![Downloads](https://img.shields.io/pypi/dm/mcp-test-harness-fastmcp)](https://pypi.org/project/mcp-test-harness-fastmcp/) |
| `mcp-test-harness-openai` | OpenAI function calling | [![PyPI](https://img.shields.io/pypi/v/mcp-test-harness-openai)](https://pypi.org/project/mcp-test-harness-openai/) | [![Downloads](https://img.shields.io/pypi/dm/mcp-test-harness-openai)](https://pypi.org/project/mcp-test-harness-openai/) |
| `mcp-test-harness-anthropic` | Anthropic Claude tool use | [![PyPI](https://img.shields.io/pypi/v/mcp-test-harness-anthropic)](https://pypi.org/project/mcp-test-harness-anthropic/) | [![Downloads](https://img.shields.io/pypi/dm/mcp-test-harness-anthropic)](https://pypi.org/project/mcp-test-harness-anthropic/) |
| `mcp-test-harness-bedrock` | AWS Bedrock agents | [![PyPI](https://img.shields.io/pypi/v/mcp-test-harness-bedrock)](https://pypi.org/project/mcp-test-harness-bedrock/) | [![Downloads](https://img.shields.io/pypi/dm/mcp-test-harness-bedrock)](https://pypi.org/project/mcp-test-harness-bedrock/) |
| `mcp-test-harness-gemini` | Google Gemini | [![PyPI](https://img.shields.io/pypi/v/mcp-test-harness-gemini)](https://pypi.org/project/mcp-test-harness-gemini/) | [![Downloads](https://img.shields.io/pypi/dm/mcp-test-harness-gemini)](https://pypi.org/project/mcp-test-harness-gemini/) |
| `mcp-test-harness-langchain` | LangChain MCP tools | [![PyPI](https://img.shields.io/pypi/v/mcp-test-harness-langchain)](https://pypi.org/project/mcp-test-harness-langchain/) | [![Downloads](https://img.shields.io/pypi/dm/mcp-test-harness-langchain)](https://pypi.org/project/mcp-test-harness-langchain/) |
| `mcp-test-harness-crewai` | CrewAI agents | [![PyPI](https://img.shields.io/pypi/v/mcp-test-harness-crewai)](https://pypi.org/project/mcp-test-harness-crewai/) | [![Downloads](https://img.shields.io/pypi/dm/mcp-test-harness-crewai)](https://pypi.org/project/mcp-test-harness-crewai/) |
| `mcp-test-harness-llamaindex` | LlamaIndex tools | [![PyPI](https://img.shields.io/pypi/v/mcp-test-harness-llamaindex)](https://pypi.org/project/mcp-test-harness-llamaindex/) | [![Downloads](https://img.shields.io/pypi/dm/mcp-test-harness-llamaindex)](https://pypi.org/project/mcp-test-harness-llamaindex/) |
| `mcp-test-harness-groq` | Groq inference | [![PyPI](https://img.shields.io/pypi/v/mcp-test-harness-groq)](https://pypi.org/project/mcp-test-harness-groq/) | [![Downloads](https://img.shields.io/pypi/dm/mcp-test-harness-groq)](https://pypi.org/project/mcp-test-harness-groq/) |
| `mcp-test-harness-mistral` | Mistral AI | [![PyPI](https://img.shields.io/pypi/v/mcp-test-harness-mistral)](https://pypi.org/project/mcp-test-harness-mistral/) | [![Downloads](https://img.shields.io/pypi/dm/mcp-test-harness-mistral)](https://pypi.org/project/mcp-test-harness-mistral/) |
| `mcp-test-harness-cohere` | Cohere | [![PyPI](https://img.shields.io/pypi/v/mcp-test-harness-cohere)](https://pypi.org/project/mcp-test-harness-cohere/) | [![Downloads](https://img.shields.io/pypi/dm/mcp-test-harness-cohere)](https://pypi.org/project/mcp-test-harness-cohere/) |
| `mcp-test-harness-azure` | Azure OpenAI | [![PyPI](https://img.shields.io/pypi/v/mcp-test-harness-azure)](https://pypi.org/project/mcp-test-harness-azure/) | [![Downloads](https://img.shields.io/pypi/dm/mcp-test-harness-azure)](https://pypi.org/project/mcp-test-harness-azure/) |
| `mcp-test-harness-vertexai` | Google Vertex AI | [![PyPI](https://img.shields.io/pypi/v/mcp-test-harness-vertexai)](https://pypi.org/project/mcp-test-harness-vertexai/) | [![Downloads](https://img.shields.io/pypi/dm/mcp-test-harness-vertexai)](https://pypi.org/project/mcp-test-harness-vertexai/) |
| `mcp-test-harness-huggingface` | Hugging Face Inference | [![PyPI](https://img.shields.io/pypi/v/mcp-test-harness-huggingface)](https://pypi.org/project/mcp-test-harness-huggingface/) | [![Downloads](https://img.shields.io/pypi/dm/mcp-test-harness-huggingface)](https://pypi.org/project/mcp-test-harness-huggingface/) |
| `mcp-test-harness-deepseek` | DeepSeek AI | [![PyPI](https://img.shields.io/pypi/v/mcp-test-harness-deepseek)](https://pypi.org/project/mcp-test-harness-deepseek/) | [![Downloads](https://img.shields.io/pypi/dm/mcp-test-harness-deepseek)](https://pypi.org/project/mcp-test-harness-deepseek/) |
| `mcp-test-harness-together` | Together AI | [![PyPI](https://img.shields.io/pypi/v/mcp-test-harness-together)](https://pypi.org/project/mcp-test-harness-together/) | [![Downloads](https://img.shields.io/pypi/dm/mcp-test-harness-together)](https://pypi.org/project/mcp-test-harness-together/) |
| `mcp-test-harness-fireworks` | Fireworks AI | [![PyPI](https://img.shields.io/pypi/v/mcp-test-harness-fireworks)](https://pypi.org/project/mcp-test-harness-fireworks/) | [![Downloads](https://img.shields.io/pypi/dm/mcp-test-harness-fireworks)](https://pypi.org/project/mcp-test-harness-fireworks/) |

## Related Projects

| Project | Purpose |
|---------|---------|
| [MCP-Bastion](https://github.com/vaquarkhan/MCP-Bastion) | Security middleware for MCP servers (prompt injection, PII, rate limiting, RBAC) |
| [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) | Official Python SDK for building MCP servers and clients |
| [MCP Inspector](https://github.com/modelcontextprotocol/inspector) | Visual debugging tool for MCP servers (manual, browser-based) |

Third-party **testing and evaluation** tools (e.g. official conformance, agent-centric evals, model benchmarks) are mapped in **[docs/COMPARISON.md](docs/COMPARISON.md)** so you can pick the right tool for the job.

## License and citation

The **mcp-test-harness** core is distributed under the **[MIT License](https://opensource.org/licenses/MIT)** — see the **[LICENSE](LICENSE)** file in this repository. That includes **commercial** use, modification, and distribution, subject to preserving the copyright and license notice.

**Citing the project (optional):** the **[CITATION.cff](CITATION.cff)** file provides metadata for academic or technical citations; it is not a legal requirement of the license.

Optional sub-packages under `packages/` may specify different license metadata in their own `pyproject.toml` files.

Author: [Vaquar Khan](https://github.com/vaquarkhan)
