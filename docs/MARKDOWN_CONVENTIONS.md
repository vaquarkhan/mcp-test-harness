# Markdown: highlighting **features** and callouts

Use this pattern so “what is a **feature** vs body text” is obvious on **GitHub** and in the **VS Code / Cursor** Markdown preview.

## GitHub “alert” blocks (recommended for features)

[GitHub Flavored Markdown](https://github.blog/changelog/2021-10-20-markdown-color-syntax-highlights-in-discussions-and-issues-and-more/) supports colored callouts. They render in the GitHub web UI; local preview depends on the theme.

```markdown
> [!TIP]
> **Feature — parallel runs:** set `test.parallel: true` in `mcp-test.yaml` or use `--parallel` on the CLI.

> [!NOTE]
> **Feature — discovery:** the harness looks for `test_*.py` and `test_` / `test__` function names (see the Developer Guide).

> [!IMPORTANT]
> **Feature — coverage gate:** 100% line coverage applies to all of `mcp_test_harness` *except* `stdio_mcp.py` (omitted on purpose; see [DEVELOPER.md](DEVELOPER.md#stdio_mcp-and-the-coverage-gate)).
```

| Alert | When to use |
|-------|-------------|
| `[!TIP]` | Product **features**, shortcuts, and “try this” |
| `[!NOTE]` | Neighboring context, file locations, or defaults |
| `[!IMPORTANT]` | Policies, security-related testing notes, or **must-read** behavior |
| `[!WARNING]` / `[!CAUTION]` | Destructive actions or breaking changes |

**Readable everywhere:** if you need plain Markdown without alert rendering, use a bold lead and a blockquote:

```markdown
> **Feature:** JUnit and JSON reports — set `report.format` and `report.output` in `mcp-test.yaml`.
```

## Code blocks and languages

Fenced code keeps syntax colors in GitHub and the editor. Always tag the language when it is not plain text:

````markdown
```bash
mcp-test --parallel
```

```yaml
server:
  command: python -m my_server
```

```python
from mcp_test_harness import marker
```
````

## Examples folder

[FEATURES_INDEX.md](../examples/FEATURES_INDEX.md) and [examples/README.md](../examples/README.md) use the **Feature** + table pattern at the top; you can add `[!TIP]` there for a stronger visual “feature” highlight.

**Related:** [EDITORS.md](EDITORS.md) (preview, Mermaid, recommended extensions)
