"""Compile experiment templates into runnable HarnessCase objects."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Awaitable, Callable

from mcp_test_harness.assertions import assert_tool_call
from mcp_test_harness.chaos import ChaosFaultError
from mcp_test_harness.discovery import HarnessCase
from mcp_test_harness.experiments.models import ExperimentTemplate
from mcp_test_harness.generate import example_arguments
from mcp_test_harness.resiliency import (
    assert_degrades_gracefully,
    assert_reconnects,
    assert_survives_crash,
)

_EXPERIMENT_MODULE = Path("experiments/catalog")


def _tools_list(tools_resp: Any) -> list[Any]:
    items = getattr(tools_resp, "tools", None)
    if isinstance(items, list):
        return items
    if isinstance(tools_resp, list):
        return tools_resp
    return []


async def _tool_name_from_session(session: Any) -> str:
    tools_resp = await session.list_tools()
    items = _tools_list(tools_resp)
    if not items:
        raise AssertionError("No tools available for experiment")
    first = items[0]
    name = getattr(first, "name", None)
    if name is not None:
        return str(name)
    if isinstance(first, dict):
        return str(first.get("name", "unknown"))
    return "unknown"


async def _tool_args_for(session: Any, tool_name: str) -> dict[str, Any]:
    tools_resp = await session.list_tools()
    items = _tools_list(tools_resp)
    for tool in items:
        name = getattr(tool, "name", None)
        if name is None and isinstance(tool, dict):
            name = tool.get("name")
        if str(name) != tool_name:
            continue
        schema = getattr(tool, "inputSchema", None)
        if schema is None and isinstance(tool, dict):
            schema = tool.get("inputSchema")
        if isinstance(schema, dict) and schema.get("properties"):
            return example_arguments(schema)
        break
    return {"text": "harness-experiment"}


async def _resolve_target(session: Any, template: ExperimentTemplate) -> tuple[str, dict[str, Any]]:
    tool = template.target_tool or await _tool_name_from_session(session)
    args = await _tool_args_for(session, tool)
    return tool, args


async def _latency_survives(session: Any, template: ExperimentTemplate) -> None:
    tool, args = await _resolve_target(session, template)
    await assert_tool_call(session, tool, args)


async def _partial_response_survives(session: Any, template: ExperimentTemplate) -> None:
    tool, args = await _resolve_target(session, template)
    result = await session.call_tool(tool, args)
    content = getattr(result, "content", None)
    assert content is not None, "truncated response should still return content"


async def _degrades_gracefully(session: Any, template: ExperimentTemplate) -> None:
    tool, _ = await _resolve_target(session, template)
    await assert_degrades_gracefully(session, tool, {"__mcp_harness_probe_invalid__": True})


async def _reconnects(session: Any, template: ExperimentTemplate) -> None:
    tool, args = await _resolve_target(session, template)
    await assert_reconnects(session, tool, args, probe_errors=3)


async def _survives_crash(session: Any, template: ExperimentTemplate) -> None:
    tool, args = await _resolve_target(session, template)
    await assert_survives_crash(session, tool, args, error_burst=5)


async def _gateway_503(session: Any, template: ExperimentTemplate) -> None:
    tool, args = await _resolve_target(session, template)
    try:
        await session.call_tool(tool, args)
        raise AssertionError("expected simulated 503 from chaos fault")
    except ChaosFaultError as exc:
        assert exc.code == 503


async def _schema_drift_survives(session: Any, template: ExperimentTemplate) -> None:
    tool, args = await _resolve_target(session, template)
    drift_args = dict(args)
    if "text" in drift_args:
        drift_args["text"] = '{"user_id": 1}'
    result = await session.call_tool(tool, drift_args)
    content = getattr(result, "content", None) or []
    assert content, "schema drift response should include content"


_ASSERTION_HANDLERS: dict[str, Callable[..., Awaitable[None]]] = {
    "latency_survives": _latency_survives,
    "partial_response_survives": _partial_response_survives,
    "degrades_gracefully": _degrades_gracefully,
    "reconnects": _reconnects,
    "survives_crash": _survives_crash,
    "gateway_503": _gateway_503,
    "schema_drift_survives": _schema_drift_survives,
}


def _markers_for(template: ExperimentTemplate) -> dict[str, Any]:
    tags = ["experiment", "resiliency", f"experiment:{template.id}"]
    if template.fault.chaos_faults:
        tags.append("chaos")
    markers: dict[str, Any] = {"tags": tags, "experiment_id": template.id}
    if template.fault.chaos_faults:
        markers["chaos_faults"] = list(template.fault.chaos_faults)
    if template.timeout is not None:
        markers["timeout"] = float(template.timeout)
    if template.status == "planned":
        markers["skip"] = True
        markers["reason"] = "experiment fault not yet implemented (planned)"
    return markers


def _make_test_func(
    template: ExperimentTemplate,
    handler: Callable[..., Awaitable[None]],
) -> Callable[..., Awaitable[None]]:
    async def test_experiment(mcp_server: Any) -> None:
        await handler(mcp_server, template)

    test_experiment.__name__ = f"test_experiment_{template.id.replace('-', '_')}"
    test_experiment.__doc__ = template.hypothesis
    return test_experiment


def compile_experiment(template: ExperimentTemplate) -> HarnessCase:
    """Compile a catalog template into a synthetic harness case."""
    if template.status == "planned":
        async def _planned_skip(mcp_server: Any) -> None:  # noqa: ARG001
            raise AssertionError("planned experiment")

        func: Callable[..., Awaitable[None]] = _planned_skip
        markers = _markers_for(template)
        markers["skip"] = True
        markers["reason"] = f"{template.title}: fault not yet implemented (planned)"
    else:
        handler = _ASSERTION_HANDLERS.get(template.assertion)
        if handler is None:
            raise ValueError(f"Unknown assertion {template.assertion!r} for {template.id}")
        func = _make_test_func(template, handler)
        markers = _markers_for(template)

    module_path = _EXPERIMENT_MODULE / f"{template.id}.yaml"
    return HarnessCase(
        name=func.__name__,
        module_path=module_path,
        func=func,
        markers=markers,
        is_async=True,
    )


def compile_experiments(templates: list[ExperimentTemplate]) -> list[HarnessCase]:
    """Compile multiple templates."""
    return [compile_experiment(t) for t in templates]
