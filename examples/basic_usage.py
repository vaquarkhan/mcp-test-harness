#!/usr/bin/env python3
"""
Basic usage examples for both packages in this repository.

Run:
    python examples/basic_usage.py

Prerequisites:
    pip install -e ".[dev]"
"""

from __future__ import annotations


def check_mcplint() -> None:
    """Check that MCP-Bastion dependencies are installed via mcplint."""
    from mcplint import bastion_version, bedrock_version

    print("--- MCPLint: Dependency Check ---\n")

    bv = bastion_version()
    print(f"  mcp-bastion-python : {bv}")

    bedrock = bedrock_version()
    if bedrock:
        print(f"  mcp-bastion-bedrock: {bedrock}")
    else:
        print("  mcp-bastion-bedrock: not installed (optional)")
        print("    -> install with: pip install -e '.[bedrock]'")


def check_test_harness() -> None:
    """Check that the MCP Test Harness is installed and importable."""
    from mcp_test_harness import __version__

    print(f"\n--- MCP Test Harness: v{__version__} ---\n")
    print("  Available assertions:")
    print("    assert_tool_call     -- invoke a tool and validate the response")
    print("    assert_resource_read -- read a resource and check content/MIME type")
    print("    assert_prompt        -- get a prompt and validate message structure")
    print("    assert_capabilities  -- verify server capabilities")
    print("    assert_snapshot      -- compare response against stored snapshot")
    print()
    print("  Run tests with:")
    print('    mcp-test --server-command "python my_server.py" tests/')
    print()
    print("  Or create mcp-test.yaml and run:")
    print("    mcp-test")


if __name__ == "__main__":
    check_mcplint()
    check_test_harness()
    print("\nAll good.")
