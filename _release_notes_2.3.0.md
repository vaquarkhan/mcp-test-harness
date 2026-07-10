## Summary

- Version bump to **2.3.0** across all 18 PyPI artifacts
- **Inspector pairing** docs in `docs/COMPARISON.md` (local sandbox → harness tests → CI)
- Docs and Action examples pin `@v2.3.0`

## Install

```bash
pip install mcp-test-harness==2.3.0
```

```yaml
- uses: vaquarkhan/mcp-test-harness@v2.3.0
  with:
    server-command: "python my_server.py"
    pr-comment: "true"
```

## Marketplace

Edit this release and check **Publish this Action to the GitHub Marketplace** (or open `action.yml` and use the banner). Requires the Marketplace Developer Agreement once.

Full notes: CHANGELOG.md `[2.3.0]`
