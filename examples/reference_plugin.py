#!/usr/bin/env python3
"""Reference plugin for the MCP Test Harness.

This module demonstrates how to build a plugin that follows the
:class:`~mcp_test_harness.plugins.MCPTestPlugin` protocol.  It registers
a custom assertion, a custom fixture, and a custom reporter.

Usage
-----
**Via config file** -- add the file path to the ``plugins`` list in your
``mcp-test.yaml``::

    plugins:
      - examples/reference_plugin.py

**Via entry point** -- declare the plugin in your package's
``pyproject.toml`` so it is discovered automatically::

    [project.entry-points.mcp_test_harness]
    latency = "my_package.reference_plugin:plugin"

In the entry-point case, the registry loads the ``plugin`` module-level
object (an instance of :class:`LatencyPlugin`).

Requirements: 9.6
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from mcp_test_harness.assertions import MCPAssertionError
from mcp_test_harness.fixtures import FixtureScope
from mcp_test_harness.models import SessionResults, CaseStatus
from mcp_test_harness.plugins import PluginContext


# ---------------------------------------------------------------------------
# Custom assertion
# ---------------------------------------------------------------------------


async def assert_response_time(
    session: Any,
    tool_name: str,
    arguments: dict[str, Any],
    max_ms: float = 500.0,
) -> Any:
    """Assert that a tool call completes within *max_ms* milliseconds.

    Parameters
    ----------
    session:
        An MCP ``ClientSession`` (or duck-typed equivalent).
    tool_name:
        Name of the tool to invoke.
    arguments:
        Arguments dict passed to the tool.
    max_ms:
        Maximum acceptable latency in milliseconds.

    Returns
    -------
    The raw result from ``session.call_tool``.

    Raises
    ------
    MCPAssertionError
        When the tool call takes longer than *max_ms*.
    """
    start = time.monotonic()
    result = await session.call_tool(tool_name, arguments)
    elapsed_ms = (time.monotonic() - start) * 1000.0

    if elapsed_ms > max_ms:
        raise MCPAssertionError(
            f"Tool '{tool_name}' took {elapsed_ms:.1f}ms "
            f"(limit: {max_ms:.1f}ms)",
        )

    return result


# ---------------------------------------------------------------------------
# Custom fixture
# ---------------------------------------------------------------------------


def test_config_factory() -> dict[str, Any]:
    """Factory for the ``test_config`` fixture.

    Returns a configuration dict that tests can request by declaring a
    ``test_config`` parameter::

        async def test_my_tool(mcp_server, test_config):
            timeout = test_config["timeout"]
            ...

    Because the scope is ``PER_MODULE``, the same dict is shared across
    all tests in a module.
    """
    return {
        "timeout": 30.0,
        "retry_count": 2,
        "server_name": "my-mcp-server",
        "tags": ["smoke", "integration"],
    }


# ---------------------------------------------------------------------------
# Custom reporter
# ---------------------------------------------------------------------------


class MarkdownReporter:
    """Reporter that generates a Markdown summary of the test run.

    The output is suitable for pasting into a pull-request comment or
    saving as a ``.md`` file.
    """

    def generate(self, results: SessionResults) -> str:
        """Return a Markdown-formatted test report.

        Parameters
        ----------
        results:
            Aggregated results from the test run.

        Returns
        -------
        str
            A Markdown string with a summary table and per-test details.
        """
        lines: list[str] = [
            "# MCP Test Report",
            "",
            f"**Protocol version:** {results.protocol_version}  ",
            f"**Duration:** {results.total_duration_ms:.1f}ms",
            "",
            "## Summary",
            "",
            "| Status | Count |",
            "|--------|-------|",
            f"| PASS   | {results.passed} |",
            f"| FAIL   | {results.failed} |",
            f"| ERROR  | {results.errored} |",
            f"| SKIP   | {results.skipped} |",
            "",
            "## Results",
            "",
            "| Test | Status | Duration |",
            "|------|--------|----------|",
        ]

        for tr in results.test_results:
            icon = _status_icon(tr.status)
            flaky_tag = " *(flaky)*" if tr.flaky else ""
            lines.append(
                f"| {tr.name} | {icon} {tr.status.value}{flaky_tag} "
                f"| {tr.duration_ms:.1f}ms |"
            )

        # Append failure details if any
        failures = [
            tr
            for tr in results.test_results
            if tr.status in (CaseStatus.FAILED, CaseStatus.ERROR)
        ]
        if failures:
            lines.append("")
            lines.append("## Failure Details")
            for tr in failures:
                lines.append("")
                lines.append(f"### {tr.name}")
                if tr.error:
                    lines.append("")
                    lines.append(f"**Error:** {tr.error}")
                if tr.assertion_diff:
                    lines.append("")
                    lines.append("```diff")
                    lines.append(tr.assertion_diff)
                    lines.append("```")

        return "\n".join(lines)


def _status_icon(status: CaseStatus) -> str:
    """Return a text label for the given test status."""
    return {
        CaseStatus.PASSED: "PASS",
        CaseStatus.FAILED: "FAIL",
        CaseStatus.ERROR: "ERROR",
        CaseStatus.TIMEOUT: "TIMEOUT",
        CaseStatus.SKIPPED: "SKIP",
    }.get(status, "?")


# ---------------------------------------------------------------------------
# Plugin class  (implements MCPTestPlugin protocol)
# ---------------------------------------------------------------------------


class LatencyPlugin:
    """Reference plugin demonstrating the MCPTestPlugin protocol.

    Registers:
    - ``assert_response_time`` -- custom assertion checking tool latency
    - ``test_config`` -- per-module fixture providing test configuration
    - ``markdown`` -- reporter that generates a Markdown summary
    """

    name: str = "latency"

    def register(self, context: PluginContext) -> None:
        """Register all extensions with the harness.

        Parameters
        ----------
        context:
            The :class:`~mcp_test_harness.plugins.PluginContext` provided
            by the plugin registry during loading.
        """
        # 1. Custom assertion
        context.add_assertion("assert_response_time", assert_response_time)

        # 2. Custom fixture (per-module scope so it's shared across tests)
        context.add_fixture(
            "test_config",
            test_config_factory,
            scope=FixtureScope.PER_MODULE,
        )

        # 3. Custom reporter
        context.add_reporter("markdown", MarkdownReporter())


# Module-level instance used by entry-point discovery.
plugin = LatencyPlugin()
