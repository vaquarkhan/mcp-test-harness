"""Unit tests for vendor package helpers (packages/mcp-test-harness-*)."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ROOT / "packages"


def _ensure_package_on_path(slug: str) -> str:
    mod = f"mcp_test_harness_{slug.replace('-', '_')}"
    src = PACKAGES / f"mcp-test-harness-{slug}" / "src"
    path = str(src)
    if path not in sys.path:
        sys.path.insert(0, path)
    return mod


@pytest.mark.parametrize(
    "slug,convert_attr,expected_keys",
    [
        ("openai", "mcp_tools_to_openai_functions", ("type", "function")),
        ("anthropic", "mcp_tools_to_anthropic_tools", ("name", "input_schema")),
        ("bedrock", "mcp_tools_to_bedrock_tool_specs", ("toolSpec",)),
        ("gemini", "mcp_tools_to_gemini_function_declarations", ("name", "parameters")),
        ("langchain", "mcp_tools_to_langchain_tools", ("name", "args_schema")),
        ("autogen", "mcp_tools_to_autogen_functions", ("name", "parameters")),
        ("ollama", "mcp_tools_to_ollama_functions", ("type", "function")),
        ("openrouter", "mcp_tools_to_openrouter_functions", ("type", "function")),
        ("litellm", "mcp_tools_to_litellm_functions", ("type", "function")),
        ("xai", "mcp_tools_to_xai_functions", ("type", "function")),
    ],
)
def test_schema_converters(slug, convert_attr, expected_keys):
    mod_name = _ensure_package_on_path(slug)
    mod = __import__(mod_name)
    convert = getattr(mod, convert_attr)
    tools = [
        {
            "name": "echo",
            "description": "Echo text",
            "inputSchema": {
                "type": "object",
                "properties": {"message": {"type": "string", "description": "msg"}},
                "required": ["message"],
            },
        }
    ]
    out = convert(tools)
    assert len(out) == 1
    for key in expected_keys:
        assert key in out[0]


def test_openai_config_and_version():
    mod_name = _ensure_package_on_path("openai")
    mod = __import__(mod_name)
    assert mod.__version__ == "3.0.10"
    cfg = mod.create_openai_test_config("python server.py", timeout=12, env={"A": "1"})
    assert cfg["server"]["command"] == "python server.py"
    assert cfg["server"]["env"] == {"A": "1"}
    assert cfg["test"]["timeout"] == 12


@pytest.mark.asyncio
async def test_assert_openai_tool_text_match_and_mismatch():
    mod_name = _ensure_package_on_path("openai")
    mod = __import__(mod_name)

    class _Session:
        async def call_tool(self, name, arguments):
            return SimpleNamespace(
                content=[SimpleNamespace(text="ok")],
                isError=False,
            )

    # Patch via core path used by helpers: assert_tool_call will use session.call_tool
    # when available through the harness — use a stub that matches assert_tool_call.
    from mcp_test_harness import MCPAssertionError
    import mcp_test_harness_openai.helpers as helpers

    async def _ok_call(session, tool_name, arguments=None, **kwargs):
        return SimpleNamespace(content=[SimpleNamespace(text="ok")])

    helpers.assert_tool_call = _ok_call  # type: ignore[attr-defined]

    result = await mod.assert_openai_tool(_Session(), "echo", {}, expected_text="ok")
    assert result.content[0].text == "ok"

    with pytest.raises(MCPAssertionError, match="text mismatch"):
        await mod.assert_openai_tool(_Session(), "echo", {}, expected_text="nope")


def test_cohere_parameter_definitions():
    mod_name = _ensure_package_on_path("cohere")
    mod = __import__(mod_name)
    out = mod.mcp_tools_to_cohere_tools(
        [
            {
                "name": "search",
                "description": "Search",
                "inputSchema": {
                    "type": "object",
                    "properties": {"q": {"type": "string", "description": "query"}},
                    "required": ["q"],
                },
            }
        ]
    )
    assert out[0]["parameter_definitions"][0]["name"] == "q"
    assert out[0]["parameter_definitions"][0]["required"] is True


def test_fastmcp_exports():
    mod_name = _ensure_package_on_path("fastmcp")
    mod = __import__(mod_name)
    assert hasattr(mod, "assert_fastmcp_tool")
    assert hasattr(mod, "create_fastmcp_test_config")
    cfg = mod.create_fastmcp_test_config("app.py", timeout=9)
    assert "python app.py" in cfg["server"]["command"]
    assert cfg["test"]["timeout"] == 9
