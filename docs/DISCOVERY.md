# Discovery and registries (MCP ecosystem)

Many installs come from **CI**, **mirrors**, and **transitive** dependencies—not only manual `pip install`. Listing MCP Test Harness where developers search for MCP **testing and automation** tools increases legitimate machine and human traffic.

Use this as an **internal checklist** when promoting releases (URLs and forms change; verify on each site).

| Platform | Suggested action |
|----------|------------------|
| **Official MCP Registry** | When publishing [tags](https://github.com/vaquarkhan/mcp-test-harness), keep the repo [server.json](../server.json) and PyPI [project] metadata (`name`, `description`, [project.urls] **Homepage** / **Repository** in [pyproject.toml](../pyproject.toml)) aligned. This project is a **test harness and CLI** that drives MCP servers; it is *not* an MCP server implementation—describe it accurately in any listing. |
| **Smithery** | If you ship an MCP *server* that includes or documents harness-based tests, you can still cross-link; for the harness package itself, prefer **PyPI** and **GitHub** as primary discovery. |
| **[Glama](https://glama.ai/)** | Claim or add a listing (testing / developer tooling) with an accurate short description and repo link. |
| **Docker** | The repo [Dockerfile](../Dockerfile) is documented in the root [README.md](../README.md#docker). Point catalog readers at that section when a container path matters. |
| **Awesome lists** | Propose a one-line entry to curated **awesome-mcp-servers** / **awesome-mcp** / **awesome-testing** lists with a stable doc link—start from [QUICK_START.md](QUICK_START.md) or the [docs hub](README.md). |
| **Companion: MCP-Bastion** | Optional runtime security: [MCP-Bastion](https://github.com/vaquarkhan/MCP-Bastion) — see that repo’s [docs/DISCOVERY.md](https://github.com/vaquarkhan/MCP-Bastion/blob/main/docs/DISCOVERY.md) for registry-oriented promotion. |

**PyPI / keywords:** keep [project] `keywords` and `classifiers` in [pyproject.toml](../pyproject.toml) current; the optional [mcplint] extra is a separate **install path** and should be mentioned in README when relevant.

**Ecosystem context:** for how this project relates to inspectors, conformance suites, and **evals**, see [COMPARISON.md](COMPARISON.md).
