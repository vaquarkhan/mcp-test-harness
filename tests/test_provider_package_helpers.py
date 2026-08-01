"""Unit tests for every vendor package under packages/mcp-test-harness-*."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from mcp_test_harness import MCPAssertionError

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ROOT / "packages"

# Keep in sync with scripts/sync_provider_packages.py PROVIDERS.
# slug, convert_attr | None, expected top-level keys in converter output
ALL_PROVIDERS: list[tuple[str, str | None, tuple[str, ...]]] = [
    ("openai", "mcp_tools_to_openai_functions", ("type", "function")),
    ("anthropic", "mcp_tools_to_anthropic_tools", ("name", "input_schema")),
    ("azure", "mcp_tools_to_azure_functions", ("type", "function")),
    ("bedrock", "mcp_tools_to_bedrock_tool_specs", ("toolSpec",)),
    ("gemini", "mcp_tools_to_gemini_function_declarations", ("name", "parameters")),
    ("vertexai", "mcp_tools_to_vertexai_function_declarations", ("name", "parameters")),
    ("groq", "mcp_tools_to_groq_functions", ("type", "function")),
    ("mistral", "mcp_tools_to_mistral_functions", ("type", "function")),
    ("cohere", "mcp_tools_to_cohere_tools", ("name", "parameter_definitions")),
    ("huggingface", "mcp_tools_to_huggingface_functions", ("type", "function")),
    ("deepseek", "mcp_tools_to_deepseek_functions", ("type", "function")),
    ("together", "mcp_tools_to_together_functions", ("type", "function")),
    ("fireworks", "mcp_tools_to_fireworks_functions", ("type", "function")),
    ("langchain", "mcp_tools_to_langchain_tools", ("name", "args_schema")),
    ("llamaindex", "mcp_tools_to_llamaindex_tools", ("name", "fn_schema")),
    ("crewai", "mcp_tools_to_crewai_tools", ("name", "args")),
    ("fastmcp", None, ()),
    ("ollama", "mcp_tools_to_ollama_functions", ("type", "function")),
    ("openrouter", "mcp_tools_to_openrouter_functions", ("type", "function")),
    ("litellm", "mcp_tools_to_litellm_functions", ("type", "function")),
    ("xai", "mcp_tools_to_xai_functions", ("type", "function")),
    ("autogen", "mcp_tools_to_autogen_functions", ("name", "parameters")),
]

SAMPLE_TOOL_DICT = {
    "name": "echo",
    "description": "Echo text",
    "inputSchema": {
        "type": "object",
        "properties": {"message": {"type": "string", "description": "msg"}},
        "required": ["message"],
    },
}


def _py_ident(slug: str) -> str:
    return slug.replace("-", "_")


def _load_package(slug: str):
    mod_name = f"mcp_test_harness_{_py_ident(slug)}"
    src = PACKAGES / f"mcp-test-harness-{slug}" / "src"
    path = str(src)
    if path not in sys.path:
        sys.path.insert(0, path)
    if mod_name in sys.modules:
        return importlib.reload(sys.modules[mod_name])
    return importlib.import_module(mod_name)


def _helpers(slug: str):
    mod = _load_package(slug)
    return importlib.import_module(f"{mod.__name__}.helpers")


def _assert_name(slug: str) -> str:
    return f"assert_{_py_ident(slug)}_tool"


def _config_name(slug: str) -> str:
    return f"create_{_py_ident(slug)}_test_config"


@pytest.fixture(params=[p[0] for p in ALL_PROVIDERS], ids=[p[0] for p in ALL_PROVIDERS])
def provider_slug(request: pytest.FixtureRequest) -> str:
    return request.param


def test_all_provider_package_dirs_exist():
    slugs = {p[0] for p in ALL_PROVIDERS}
    found = {
        p.name.removeprefix("mcp-test-harness-")
        for p in PACKAGES.iterdir()
        if p.is_dir() and p.name.startswith("mcp-test-harness-")
    }
    assert slugs == found


def test_version_aligned(provider_slug: str):
    mod = _load_package(provider_slug)
    assert mod.__version__ == "3.0.10"


@pytest.mark.parametrize("slug,convert_attr,expected_keys", ALL_PROVIDERS)
def test_schema_converter_dict_and_object(slug, convert_attr, expected_keys):
    if convert_attr is None:
        pytest.skip("fastmcp has no schema converter")
    mod = _load_package(slug)
    convert = getattr(mod, convert_attr)

    out_dict = convert([SAMPLE_TOOL_DICT])
    assert len(out_dict) == 1
    for key in expected_keys:
        assert key in out_dict[0]

    tool_obj = SimpleNamespace(
        name="echo",
        description="Echo text",
        inputSchema=SAMPLE_TOOL_DICT["inputSchema"],
    )
    out_obj = convert([tool_obj])
    assert len(out_obj) == 1
    for key in expected_keys:
        assert key in out_obj[0]


def test_config_builder(provider_slug: str):
    mod = _load_package(provider_slug)
    if provider_slug == "fastmcp":
        cfg = mod.create_fastmcp_test_config("app.py", transport="sse", timeout=9)
        assert cfg["server"]["command"] == "python app.py"
        assert cfg["server"]["transport"] == "sse"
        assert cfg["test"]["timeout"] == 9
        return

    create = getattr(mod, _config_name(provider_slug))
    cfg = create("python server.py", transport="http", timeout=12, env={"A": "1"})
    assert cfg["server"]["command"] == "python server.py"
    assert cfg["server"]["transport"] == "http"
    assert cfg["server"]["env"] == {"A": "1"}
    assert cfg["test"]["timeout"] == 12

    cfg_no_env = create("python server.py")
    assert "env" not in cfg_no_env["server"]


@pytest.mark.asyncio
async def test_assert_tool_match_mismatch_empty(provider_slug: str):
    helpers = _helpers(provider_slug)
    mod = _load_package(provider_slug)
    assert_fn = getattr(
        mod,
        "assert_fastmcp_tool" if provider_slug == "fastmcp" else _assert_name(provider_slug),
    )

    async def _ok_call(session, tool_name, arguments=None, **kwargs):
        return SimpleNamespace(content=[SimpleNamespace(text="ok")])

    async def _empty_call(session, tool_name, arguments=None, **kwargs):
        return SimpleNamespace(content=[])

    helpers.assert_tool_call = _ok_call  # type: ignore[attr-defined]

    result = await assert_fn(object(), "echo", {}, expected_text="ok")
    assert result.content[0].text == "ok"

    # No expected_text — still returns result
    result2 = await assert_fn(object(), "echo", None)
    assert result2.content[0].text == "ok"

    with pytest.raises(MCPAssertionError, match="text mismatch"):
        await assert_fn(object(), "echo", {}, expected_text="nope")

    helpers.assert_tool_call = _empty_call  # type: ignore[attr-defined]
    with pytest.raises(MCPAssertionError, match="no content"):
        await assert_fn(object(), "echo", {}, expected_text="ok")


@pytest.mark.asyncio
async def test_fastmcp_resource_helper():
    helpers = _helpers("fastmcp")
    mod = _load_package("fastmcp")

    async def _read(session, uri, expected_content=None):
        return SimpleNamespace(contents=[SimpleNamespace(text=expected_content or "data")])

    helpers.assert_resource_read = _read  # type: ignore[attr-defined]
    result = await mod.assert_fastmcp_resource(object(), "config://app", expected_text="data")
    assert result.contents[0].text == "data"


def test_cohere_required_parameter_flag():
    mod = _load_package("cohere")
    out = mod.mcp_tools_to_cohere_tools([SAMPLE_TOOL_DICT])
    params = {p["name"]: p for p in out[0]["parameter_definitions"]}
    assert params["message"]["required"] is True
    assert params["message"]["type"] == "string"


def test_bedrock_tool_spec_json_schema():
    mod = _load_package("bedrock")
    out = mod.mcp_tools_to_bedrock_tool_specs([SAMPLE_TOOL_DICT])
    assert out[0]["toolSpec"]["name"] == "echo"
    assert out[0]["toolSpec"]["inputSchema"]["json"]["type"] == "object"


def test_openai_shaped_function_envelope():
    mod = _load_package("openai")
    out = mod.mcp_tools_to_openai_functions([SAMPLE_TOOL_DICT])
    assert out[0]["type"] == "function"
    assert out[0]["function"]["name"] == "echo"
    assert out[0]["function"]["parameters"]["required"] == ["message"]


def test_exports_listed_in_all():
    for slug, convert_attr, _ in ALL_PROVIDERS:
        mod = _load_package(slug)
        assert "__version__" in mod.__all__
        if slug == "fastmcp":
            for name in (
                "assert_fastmcp_tool",
                "assert_fastmcp_resource",
                "create_fastmcp_test_config",
            ):
                assert name in mod.__all__
                assert hasattr(mod, name)
            continue
        for name in (_assert_name(slug), convert_attr, _config_name(slug)):
            assert name in mod.__all__
            assert hasattr(mod, name)
