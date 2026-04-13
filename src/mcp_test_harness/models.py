"""Core data models for the MCP Test Harness."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal


# ---------------------------------------------------------------------------
# Literal type aliases
# ---------------------------------------------------------------------------

TransportType = Literal["stdio", "sse", "http"]
"""Supported MCP transport types."""

ReportFormat = Literal["json", "junit", "html"]
"""Supported report output formats."""


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class CaseStatus(Enum):
    """Outcome status for a single test case or attempt."""

    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"


# ---------------------------------------------------------------------------
# Test result dataclasses
# ---------------------------------------------------------------------------


@dataclass
class AttemptResult:
    """Result of a single execution attempt (used for retries)."""

    attempt: int
    status: CaseStatus
    duration_ms: float
    error: str | None = None


@dataclass
class CaseResult:
    """Full result for one test case, including retry history."""

    name: str
    module: str
    status: CaseStatus
    duration_ms: float
    error: str | None = None
    traceback: str | None = None
    assertion_diff: str | None = None
    retry_count: int = 0
    attempt_results: list[AttemptResult] = field(default_factory=list)
    flaky: bool = False
    schema_violations: list[SchemaViolation] = field(default_factory=list)


@dataclass
class SessionResults:
    """Aggregated results for an entire test run."""

    test_results: list[CaseResult]
    total_duration_ms: float
    server_capabilities: dict[str, Any]
    protocol_version: str
    harness_version: str
    passed: int = 0
    failed: int = 0
    errored: int = 0
    skipped: int = 0
    timed_out: int = 0


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


@dataclass
class SchemaViolation:
    """A single schema validation violation with location details."""

    json_path: str
    expected_type: str
    actual_value: Any
    message: str


# ---------------------------------------------------------------------------
# JSON-RPC message models
# ---------------------------------------------------------------------------


@dataclass
class JsonRpcError:
    """Structured JSON-RPC error object."""

    code: int
    message: str
    data: Any | None = None


@dataclass
class ParsedMessage:
    """Typed representation of a JSON-RPC message."""

    id: int | str | None
    method: str | None
    params: dict[str, Any] | None
    result: Any | None
    error: JsonRpcError | None
    raw: bytes
