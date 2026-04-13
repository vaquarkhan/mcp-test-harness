# Project decisions

Author: Vaquar Khan -- https://github.com/vaquarkhan

Short record of what we chose and why.

## 1. Monorepo: mcplint + mcp-test-harness

**Decision:** Ship both packages from one repository. `mcplint` is the dependency shim for MCP ecosystem packages. `mcp_test_harness` is the pytest-style testing framework for MCP servers.

**Why:** Shared CI, shared `pyproject.toml`, single install (`pip install -e ".[dev]"`). The test harness depends on the MCP SDK directly for client sessions and transport.

## 2. MCP-Bastion as dependency, not fork

**Decision:** Depend on `mcp-bastion-python` from PyPI as an optional security layer. Security middleware (prompt injection, PII redaction, RBAC, rate limits, policy-as-code) is a separate concern handled by [MCP-Bastion](https://github.com/vaquarkhan/MCP-Bastion).

**Why:** MCPLint focuses on testing. Security is a separate project with a separate lifecycle. MCPLint can pin it as a dependency for teams that need both.

## 3. Async-first architecture

**Decision:** The test harness core is fully async (built on `anyio`). The CLI provides the sync entry point via `asyncio.run()`.

**Why:** The MCP Python SDK is async. Fighting that with sync wrappers everywhere would add complexity and limit transport support.

## 4. pytest conventions, standalone runner

**Decision:** Test discovery follows pytest conventions (`test_*.py`, `Test` classes, `test_` functions), but the harness ships its own lightweight test runner.

**Why:** Familiar to Python developers. The standalone runner avoids a hard pytest dependency for the single-binary distribution while keeping the same developer experience.

## 5. Plugin-first extensibility

**Decision:** Custom assertions, fixtures, reporters, and transport adapters are all registered through a unified plugin registry using Python entry points and config-file paths.

**Why:** Follows the ESLint model -- let domain experts extend the tool without modifying the core. Framework-specific plugins (FastMCP, LangChain, etc.) can be authored independently.

## 6. Single binary distribution

**Decision:** Ship as a standalone binary via PyInstaller alongside the standard `pip install` path.

**Why:** Zero-friction adoption. CI pipelines can download a single binary without managing Python environments. Follows the Trivy distribution model.

## 7. GitHub Action from day one

**Decision:** Ship a composite GitHub Action (`.github/actions/mcp-test/`) that wraps the CLI.

**Why:** Every repo that adds the action becomes a visible endorsement. Self-reinforcing distribution loop through GitHub Marketplace discovery.

## 8. CI: quick vs full

**Decision:**
- Quick job (every PR): offline `pyproject.toml` pin check -- no heavy downloads
- Full job (main branch + manual): full install, import verification, all tests

**Why:** PRs stay fast (under a minute). Full validation runs on merge without blocking contributors on multi-gigabyte installs.

## 9. Transport-agnostic design

**Decision:** Transport adapters (stdio, SSE, streamable HTTP) sit behind a protocol interface. The plugin system allows custom transports.

**Why:** MCP servers use different transports. Tests should work identically regardless of how the server communicates.

## 10. Schema validation built-in

**Decision:** Every JSON-RPC response is validated against the MCP specification schemas by default. Can be disabled via config.

**Why:** Catches protocol violations automatically. Server authors don't need to write boilerplate validation code.

## 11. Non-commercial license

**Decision:** Non-commercial use only with mandatory attribution.

**Why:** Author's choice. Commercial licensing available on request.
