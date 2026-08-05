#!/usr/bin/env python3
"""Generate / refresh vendor packages under packages/ with real helpers.

Run from repo root:
  python scripts/sync_provider_packages.py --version 4.0.1
"""

from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ROOT / "packages"

# slug, title, short description, schema_kind
PROVIDERS: list[tuple[str, str, str, str]] = [
    ("openai", "OpenAI", "OpenAI function calling", "openai"),
    ("anthropic", "Anthropic", "Anthropic Claude tool use", "anthropic"),
    ("azure", "Azure OpenAI", "Azure OpenAI", "openai"),
    ("bedrock", "AWS Bedrock", "AWS Bedrock agents", "bedrock"),
    ("gemini", "Google Gemini", "Google Gemini", "gemini"),
    ("vertexai", "Google Vertex AI", "Google Vertex AI", "gemini"),
    ("groq", "Groq", "Groq inference", "openai"),
    ("mistral", "Mistral AI", "Mistral AI", "openai"),
    ("cohere", "Cohere", "Cohere", "cohere"),
    ("huggingface", "Hugging Face", "Hugging Face Inference", "openai"),
    ("deepseek", "DeepSeek", "DeepSeek AI", "openai"),
    ("together", "Together AI", "Together AI", "openai"),
    ("fireworks", "Fireworks AI", "Fireworks AI", "openai"),
    ("langchain", "LangChain", "LangChain MCP tools", "langchain"),
    ("llamaindex", "LlamaIndex", "LlamaIndex tools", "llamaindex"),
    ("crewai", "CrewAI", "CrewAI agents", "crewai"),
    ("fastmcp", "FastMCP", "FastMCP servers", "fastmcp"),
    ("ollama", "Ollama", "Ollama local models", "openai"),
    ("openrouter", "OpenRouter", "OpenRouter multi-model gateway", "openai"),
    ("litellm", "LiteLLM", "LiteLLM proxy / router", "openai"),
    ("xai", "xAI", "xAI Grok", "openai"),
    ("autogen", "AutoGen", "Microsoft AutoGen agents", "autogen"),
    ("langgraph", "LangGraph", "LangGraph agent graphs", "langchain"),
    ("pydantic-ai", "Pydantic AI", "Pydantic AI agents", "autogen"),
    ("openai-agents", "OpenAI Agents", "OpenAI Agents SDK", "openai"),
]


def py_ident(slug: str) -> str:
    return slug.replace("-", "_")


def module_name(slug: str) -> str:
    return f"mcp_test_harness_{py_ident(slug)}"


def package_dir_name(slug: str) -> str:
    return f"mcp-test-harness-{slug}"


def helpers_source(slug: str, title: str, kind: str) -> str:
    mod = module_name(slug)
    assert_fn = f"assert_{py_ident(slug)}_tool"
    config_fn = f"create_{py_ident(slug)}_test_config"
    convert_fn = {
        "openai": f"mcp_tools_to_{py_ident(slug)}_functions",
        "anthropic": f"mcp_tools_to_{py_ident(slug)}_tools",
        "bedrock": f"mcp_tools_to_{py_ident(slug)}_tool_specs",
        "gemini": f"mcp_tools_to_{py_ident(slug)}_function_declarations",
        "cohere": f"mcp_tools_to_{py_ident(slug)}_tools",
        "langchain": f"mcp_tools_to_{py_ident(slug)}_tools",
        "llamaindex": f"mcp_tools_to_{py_ident(slug)}_tools",
        "crewai": f"mcp_tools_to_{py_ident(slug)}_tools",
        "autogen": f"mcp_tools_to_{py_ident(slug)}_functions",
        "fastmcp": None,
    }[kind]

    if kind == "fastmcp":
        return '''"""FastMCP-specific testing helpers.

Provides convenience wrappers around mcp-test-harness assertions
tailored for FastMCP server patterns.
"""

from __future__ import annotations

from typing import Any

from mcp_test_harness import assert_tool_call, assert_resource_read, MCPAssertionError


async def assert_fastmcp_tool(
    session: Any,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
    expected_text: str | None = None,
) -> Any:
    """Call a FastMCP tool and optionally validate the text response."""
    args = arguments or {}
    result = await assert_tool_call(session, tool_name, args)

    if expected_text is not None:
        content = getattr(result, "content", None) or []
        if not content:
            raise MCPAssertionError(
                f"FastMCP tool '{tool_name}' returned no content"
            )
        actual_text = getattr(content[0], "text", None)
        if actual_text != expected_text:
            raise MCPAssertionError(
                f"FastMCP tool '{tool_name}' text mismatch: "
                f"expected '{expected_text}', got '{actual_text}'"
            )

    return result


async def assert_fastmcp_resource(
    session: Any,
    uri: str,
    expected_text: str | None = None,
) -> Any:
    """Read a FastMCP resource and optionally validate the text content."""
    return await assert_resource_read(
        session, uri, expected_content=expected_text
    )


def create_fastmcp_test_config(
    server_file: str = "server.py",
    transport: str = "stdio",
    timeout: int = 30,
) -> dict[str, Any]:
    """Create a config dict suitable for FastMCP server testing."""
    return {
        "server": {
            "command": f"python {server_file}",
            "transport": transport,
        },
        "test": {
            "timeout": timeout,
        },
    }
'''

    convert_impl = {
        "openai": f'''
def {convert_fn}(tools: list[Any]) -> list[dict[str, Any]]:
    """Map MCP tool objects/dicts to OpenAI function-calling tool defs."""
    out: list[dict[str, Any]] = []
    for tool in tools:
        name = getattr(tool, "name", None) or tool.get("name")
        description = getattr(tool, "description", None)
        if description is None and isinstance(tool, dict):
            description = tool.get("description", "")
        schema = getattr(tool, "inputSchema", None)
        if schema is None and isinstance(tool, dict):
            schema = tool.get("inputSchema") or tool.get("input_schema") or {{}}
        out.append({{
            "type": "function",
            "function": {{
                "name": name,
                "description": description or "",
                "parameters": schema or {{"type": "object", "properties": {{}}}},
            }},
        }})
    return out
''',
        "anthropic": f'''
def {convert_fn}(tools: list[Any]) -> list[dict[str, Any]]:
    """Map MCP tools to Anthropic Messages API tool definitions."""
    out: list[dict[str, Any]] = []
    for tool in tools:
        name = getattr(tool, "name", None) or tool.get("name")
        description = getattr(tool, "description", None)
        if description is None and isinstance(tool, dict):
            description = tool.get("description", "")
        schema = getattr(tool, "inputSchema", None)
        if schema is None and isinstance(tool, dict):
            schema = tool.get("inputSchema") or tool.get("input_schema") or {{}}
        out.append({{
            "name": name,
            "description": description or "",
            "input_schema": schema or {{"type": "object", "properties": {{}}}},
        }})
    return out
''',
        "bedrock": f'''
def {convert_fn}(tools: list[Any]) -> list[dict[str, Any]]:
    """Map MCP tools to Bedrock Converse toolSpec entries."""
    out: list[dict[str, Any]] = []
    for tool in tools:
        name = getattr(tool, "name", None) or tool.get("name")
        description = getattr(tool, "description", None)
        if description is None and isinstance(tool, dict):
            description = tool.get("description", "")
        schema = getattr(tool, "inputSchema", None)
        if schema is None and isinstance(tool, dict):
            schema = tool.get("inputSchema") or tool.get("input_schema") or {{}}
        out.append({{
            "toolSpec": {{
                "name": name,
                "description": description or "",
                "inputSchema": {{"json": schema or {{"type": "object", "properties": {{}}}}}},
            }},
        }})
    return out
''',
        "gemini": f'''
def {convert_fn}(tools: list[Any]) -> list[dict[str, Any]]:
    """Map MCP tools to Gemini / Vertex functionDeclarations."""
    out: list[dict[str, Any]] = []
    for tool in tools:
        name = getattr(tool, "name", None) or tool.get("name")
        description = getattr(tool, "description", None)
        if description is None and isinstance(tool, dict):
            description = tool.get("description", "")
        schema = getattr(tool, "inputSchema", None)
        if schema is None and isinstance(tool, dict):
            schema = tool.get("inputSchema") or tool.get("input_schema") or {{}}
        out.append({{
            "name": name,
            "description": description or "",
            "parameters": schema or {{"type": "object", "properties": {{}}}},
        }})
    return out
''',
        "cohere": f'''
def {convert_fn}(tools: list[Any]) -> list[dict[str, Any]]:
    """Map MCP tools to Cohere tool definitions."""
    out: list[dict[str, Any]] = []
    for tool in tools:
        name = getattr(tool, "name", None) or tool.get("name")
        description = getattr(tool, "description", None)
        if description is None and isinstance(tool, dict):
            description = tool.get("description", "")
        schema = getattr(tool, "inputSchema", None)
        if schema is None and isinstance(tool, dict):
            schema = tool.get("inputSchema") or tool.get("input_schema") or {{}}
        props = (schema or {{}}).get("properties") or {{}}
        parameter_defs = [
            {{
                "name": key,
                "description": (val or {{}}).get("description", ""),
                "type": (val or {{}}).get("type", "string"),
                "required": key in ((schema or {{}}).get("required") or []),
            }}
            for key, val in props.items()
        ]
        out.append({{
            "name": name,
            "description": description or "",
            "parameter_definitions": parameter_defs,
        }})
    return out
''',
        "langchain": f'''
def {convert_fn}(tools: list[Any]) -> list[dict[str, Any]]:
    """Map MCP tools to LangChain-style tool dicts (name/description/args)."""
    out: list[dict[str, Any]] = []
    for tool in tools:
        name = getattr(tool, "name", None) or tool.get("name")
        description = getattr(tool, "description", None)
        if description is None and isinstance(tool, dict):
            description = tool.get("description", "")
        schema = getattr(tool, "inputSchema", None)
        if schema is None and isinstance(tool, dict):
            schema = tool.get("inputSchema") or tool.get("input_schema") or {{}}
        out.append({{
            "name": name,
            "description": description or "",
            "args_schema": schema or {{"type": "object", "properties": {{}}}},
        }})
    return out
''',
        "llamaindex": f'''
def {convert_fn}(tools: list[Any]) -> list[dict[str, Any]]:
    """Map MCP tools to LlamaIndex FunctionTool-style metadata dicts."""
    out: list[dict[str, Any]] = []
    for tool in tools:
        name = getattr(tool, "name", None) or tool.get("name")
        description = getattr(tool, "description", None)
        if description is None and isinstance(tool, dict):
            description = tool.get("description", "")
        schema = getattr(tool, "inputSchema", None)
        if schema is None and isinstance(tool, dict):
            schema = tool.get("inputSchema") or tool.get("input_schema") or {{}}
        out.append({{
            "name": name,
            "description": description or "",
            "fn_schema": schema or {{"type": "object", "properties": {{}}}},
        }})
    return out
''',
        "crewai": f'''
def {convert_fn}(tools: list[Any]) -> list[dict[str, Any]]:
    """Map MCP tools to CrewAI-compatible tool metadata dicts."""
    out: list[dict[str, Any]] = []
    for tool in tools:
        name = getattr(tool, "name", None) or tool.get("name")
        description = getattr(tool, "description", None)
        if description is None and isinstance(tool, dict):
            description = tool.get("description", "")
        schema = getattr(tool, "inputSchema", None)
        if schema is None and isinstance(tool, dict):
            schema = tool.get("inputSchema") or tool.get("input_schema") or {{}}
        out.append({{
            "name": name,
            "description": description or "",
            "args": schema or {{"type": "object", "properties": {{}}}},
        }})
    return out
''',
        "autogen": f'''
def {convert_fn}(tools: list[Any]) -> list[dict[str, Any]]:
    """Map MCP tools to AutoGen / OpenAI-compatible function schemas."""
    out: list[dict[str, Any]] = []
    for tool in tools:
        name = getattr(tool, "name", None) or tool.get("name")
        description = getattr(tool, "description", None)
        if description is None and isinstance(tool, dict):
            description = tool.get("description", "")
        schema = getattr(tool, "inputSchema", None)
        if schema is None and isinstance(tool, dict):
            schema = tool.get("inputSchema") or tool.get("input_schema") or {{}}
        out.append({{
            "name": name,
            "description": description or "",
            "parameters": schema or {{"type": "object", "properties": {{}}}},
        }})
    return out
''',
    }[kind]

    return f'''"""{title}-specific testing helpers for MCP Test Harness.

Thin wrappers around core assertions plus MCP→{title} schema converters.
"""

from __future__ import annotations

from typing import Any

from mcp_test_harness import assert_tool_call, MCPAssertionError


async def {assert_fn}(
    session: Any,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
    expected_text: str | None = None,
) -> Any:
    """Call an MCP tool (as used from {title}) and optionally check text."""
    args = arguments or {{}}
    result = await assert_tool_call(session, tool_name, args)

    if expected_text is not None:
        content = getattr(result, "content", None) or []
        if not content:
            raise MCPAssertionError(
                f"{title} tool '{{tool_name}}' returned no content"
            )
        actual_text = getattr(content[0], "text", None)
        if actual_text != expected_text:
            raise MCPAssertionError(
                f"{title} tool '{{tool_name}}' text mismatch: "
                f"expected '{{expected_text}}', got '{{actual_text}}'"
            )

    return result

{convert_impl}

def {config_fn}(
    server_command: str,
    *,
    transport: str = "stdio",
    timeout: int = 30,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build an mcp-test.yaml-shaped config for {title} MCP testing."""
    server: dict[str, Any] = {{
        "command": server_command,
        "transport": transport,
    }}
    if env:
        server["env"] = env
    return {{
        "server": server,
        "test": {{"timeout": timeout}},
    }}
'''


def init_source(slug: str, title: str, kind: str, version: str) -> str:
    mod = module_name(slug)
    if kind == "fastmcp":
        exports = [
            "assert_fastmcp_tool",
            "assert_fastmcp_resource",
            "create_fastmcp_test_config",
        ]
    else:
        assert_fn = f"assert_{py_ident(slug)}_tool"
        config_fn = f"create_{py_ident(slug)}_test_config"
        convert_fn = {
            "openai": f"mcp_tools_to_{py_ident(slug)}_functions",
            "anthropic": f"mcp_tools_to_{py_ident(slug)}_tools",
            "bedrock": f"mcp_tools_to_{py_ident(slug)}_tool_specs",
            "gemini": f"mcp_tools_to_{py_ident(slug)}_function_declarations",
            "cohere": f"mcp_tools_to_{py_ident(slug)}_tools",
            "langchain": f"mcp_tools_to_{py_ident(slug)}_tools",
            "llamaindex": f"mcp_tools_to_{py_ident(slug)}_tools",
            "crewai": f"mcp_tools_to_{py_ident(slug)}_tools",
            "autogen": f"mcp_tools_to_{py_ident(slug)}_functions",
        }[kind]
        exports = [assert_fn, convert_fn, config_fn]

    export_list = ",\n    ".join(exports)
    all_list = '",\n    "'.join(["__version__", *exports])
    return f'''"""MCP Test Harness helpers for {title} testing."""

from __future__ import annotations

__version__ = "{version}"

from {mod}.helpers import (
    {export_list},
)

__all__ = [
    "{all_list}",
]
'''


def readme_source(slug: str, title: str, short: str, kind: str) -> str:
    pkg = package_dir_name(slug)
    mod = module_name(slug)
    if kind == "fastmcp":
        usage = f'''```python
from {mod} import assert_fastmcp_tool, assert_fastmcp_resource

async def test_echo(mcp_server):
    await assert_fastmcp_tool(mcp_server, "echo", {{"message": "hi"}}, expected_text="hi")

async def test_config(mcp_server):
    await assert_fastmcp_resource(mcp_server, "config://app", expected_text='{{"debug": true}}')
```'''
    else:
        assert_fn = f"assert_{py_ident(slug)}_tool"
        convert_fn = {
            "openai": f"mcp_tools_to_{py_ident(slug)}_functions",
            "anthropic": f"mcp_tools_to_{py_ident(slug)}_tools",
            "bedrock": f"mcp_tools_to_{py_ident(slug)}_tool_specs",
            "gemini": f"mcp_tools_to_{py_ident(slug)}_function_declarations",
            "cohere": f"mcp_tools_to_{py_ident(slug)}_tools",
            "langchain": f"mcp_tools_to_{py_ident(slug)}_tools",
            "llamaindex": f"mcp_tools_to_{py_ident(slug)}_tools",
            "crewai": f"mcp_tools_to_{py_ident(slug)}_tools",
            "autogen": f"mcp_tools_to_{py_ident(slug)}_functions",
        }[kind]
        config_fn = f"create_{py_ident(slug)}_test_config"
        usage = f'''```python
from {mod} import {assert_fn}, {convert_fn}, {config_fn}

async def test_tool(mcp_server):
    await {assert_fn}(mcp_server, "my_tool", {{}}, expected_text="ok")

def test_schema_bridge(mcp_tools):
    # mcp_tools from list_tools — convert for {title} SDKs
    return {convert_fn}(mcp_tools)

cfg = {config_fn}("python server.py", timeout=45)
```'''

    return f'''# {pkg}

{short} testing helpers for [MCP Test Harness](https://github.com/vaquarkhan/mcp-test-harness).

Author: Vaquar Khan -- https://github.com/vaquarkhan

## Install

```bash
pip install {pkg}
```

This automatically installs `mcp-test-harness` as a dependency.

## Usage

{usage}

## Helpers

- Tool call assertion with optional text check
- MCP tool → {title} schema converter
- `mcp-test.yaml`-shaped config builder

## License

Non-commercial use only with mandatory attribution. See [LICENSE](https://github.com/vaquarkhan/mcp-test-harness/blob/main/LICENSE).
'''


def pyproject_source(slug: str, title: str, short: str, version: str) -> str:
    pkg = package_dir_name(slug)
    mod = module_name(slug)
    return f'''[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "{pkg}"
version = "{version}"
description = "{short} testing helpers for MCP Test Harness"
readme = "README.md"
requires-python = ">=3.10"
license = {{text = "Non-commercial use only with mandatory attribution"}}
authors = [{{name = "Vaquar Khan", email = "vaquarkhan@gmail.com"}}]
keywords = ["mcp", "{slug}", "testing", "mcp-test-harness"]
classifiers = [
  "Development Status :: 5 - Production/Stable",
  "Intended Audience :: Developers",
  "Programming Language :: Python :: 3",
  "Topic :: Software Development :: Testing",
]
dependencies = [
  "mcp-test-harness>={version}",
]

[project.urls]
Homepage = "https://github.com/vaquarkhan/mcp-test-harness"
Repository = "https://github.com/vaquarkhan/mcp-test-harness"

[tool.hatch.build.targets.wheel]
packages = ["src/{mod}"]
'''


def write_package(slug: str, title: str, short: str, kind: str, version: str) -> None:
    pkg = package_dir_name(slug)
    mod = module_name(slug)
    base = PACKAGES / pkg
    src = base / "src" / mod
    src.mkdir(parents=True, exist_ok=True)
    (src / "helpers.py").write_text(helpers_source(slug, title, kind), encoding="utf-8")
    (src / "__init__.py").write_text(init_source(slug, title, kind, version), encoding="utf-8")
    (base / "README.md").write_text(readme_source(slug, title, short, kind), encoding="utf-8")
    (base / "pyproject.toml").write_text(pyproject_source(slug, title, short, version), encoding="utf-8")
    print(f"wrote {pkg}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    PACKAGES.mkdir(exist_ok=True)
    for slug, title, short, kind in PROVIDERS:
        write_package(slug, title, short, kind, args.version)
    print(f"synced {len(PROVIDERS)} packages at {args.version}")


if __name__ == "__main__":
    main()
