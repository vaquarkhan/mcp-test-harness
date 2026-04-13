"""Configuration loading and validation for the MCP Test Harness.

Loads configuration from YAML/TOML files and CLI flags, with CLI flags
taking precedence over config file values.
"""

from __future__ import annotations

import logging
import tomllib
from argparse import Namespace
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from mcp_test_harness.models import ReportFormat, TransportType

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Known config keys (for unknown-key warnings)
# ---------------------------------------------------------------------------

_KNOWN_TOP_KEYS = frozenset(
    {
        "server",
        "test",
        "report",
        "schema_validation",
        "plugins",
        "redact_patterns",
    }
)

_KNOWN_SERVER_KEYS = frozenset({"command", "transport", "transport_options"})
_KNOWN_TEST_KEYS = frozenset({"dirs", "timeout", "parallel", "workers"})
_KNOWN_REPORT_KEYS = frozenset({"format", "output"})


# ---------------------------------------------------------------------------
# Error model
# ---------------------------------------------------------------------------


@dataclass
class ConfigError:
    """A single configuration validation error with optional line number."""

    message: str
    line: int | None = None


# ---------------------------------------------------------------------------
# HarnessConfig
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HarnessConfig:
    """Immutable configuration for a test harness run."""

    server_command: str
    transport: TransportType = "stdio"
    transport_options: dict[str, Any] = field(default_factory=dict)
    timeout: float = 30.0
    test_dirs: list[str] = field(default_factory=lambda: ["tests/"])
    report_format: ReportFormat | None = None
    report_output: str | None = None
    plugins: list[str] = field(default_factory=list)
    parallel: bool = False
    workers: int | None = None
    verbose: bool = False
    update_snapshots: bool = False
    schema_validation: bool = True
    filter_name: str | None = None
    filter_marker: str | None = None


# ---------------------------------------------------------------------------
# Config file discovery
# ---------------------------------------------------------------------------

_AUTO_NAMES = ("mcp-test.yaml", "mcp-test.yml", "mcp-test.toml")


def _discover_config_file(cwd: Path | None = None) -> Path | None:
    """Return the first auto-discovered config file in *cwd*, or ``None``."""
    base = cwd or Path.cwd()
    for name in _AUTO_NAMES:
        candidate = base / name
        if candidate.is_file():
            return candidate
    return None


# ---------------------------------------------------------------------------
# File parsing helpers
# ---------------------------------------------------------------------------


def _parse_yaml(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected a YAML mapping at top level in {path}")
    return data


def _parse_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as fh:
        return tomllib.load(fh)


def _parse_config_file(path: Path) -> dict[str, Any]:
    """Parse a YAML or TOML config file and return the raw dict."""
    suffix = path.suffix.lower()
    if suffix in (".yaml", ".yml"):
        return _parse_yaml(path)
    if suffix == ".toml":
        return _parse_toml(path)
    raise ValueError(
        f"Unsupported config file format '{suffix}'. Use .yaml, .yml, or .toml."
    )


# ---------------------------------------------------------------------------
# Unknown-key warnings
# ---------------------------------------------------------------------------


def _warn_unknown_keys(
    data: dict[str, Any],
    known: frozenset[str],
    section: str,
) -> None:
    """Log a warning for each key in *data* not present in *known*."""
    for key in data:
        if key not in known:
            logger.warning("Unknown config key '%s' in %s section", key, section)


# ---------------------------------------------------------------------------
# Flatten raw config dict -> kwargs for HarnessConfig
# ---------------------------------------------------------------------------


def _flatten_config(raw: dict[str, Any]) -> dict[str, Any]:
    """Convert the nested config-file structure into flat kwargs."""
    _warn_unknown_keys(raw, _KNOWN_TOP_KEYS, "top-level")

    result: dict[str, Any] = {}

    # -- server section --
    server = raw.get("server", {})
    if isinstance(server, dict):
        _warn_unknown_keys(server, _KNOWN_SERVER_KEYS, "server")
        if "command" in server:
            result["server_command"] = server["command"]
        if "transport" in server:
            result["transport"] = server["transport"]
        if "transport_options" in server:
            result["transport_options"] = server["transport_options"]

    # -- test section --
    test = raw.get("test", {})
    if isinstance(test, dict):
        _warn_unknown_keys(test, _KNOWN_TEST_KEYS, "test")
        if "dirs" in test:
            result["test_dirs"] = test["dirs"]
        if "timeout" in test:
            result["timeout"] = float(test["timeout"])
        if "parallel" in test:
            result["parallel"] = bool(test["parallel"])
        if "workers" in test:
            result["workers"] = int(test["workers"])

    # -- report section --
    report = raw.get("report", {})
    if isinstance(report, dict):
        _warn_unknown_keys(report, _KNOWN_REPORT_KEYS, "report")
        if "format" in report:
            result["report_format"] = report["format"]
        if "output" in report:
            result["report_output"] = report["output"]

    # -- top-level scalars / lists --
    if "schema_validation" in raw:
        result["schema_validation"] = bool(raw["schema_validation"])
    if "plugins" in raw:
        result["plugins"] = raw["plugins"]

    return result


# ---------------------------------------------------------------------------
# Merge CLI namespace on top of file config
# ---------------------------------------------------------------------------

# Maps CLI attribute names -> HarnessConfig field names
_CLI_MAP: dict[str, str] = {
    "server_command": "server_command",
    "transport": "transport",
    "timeout": "timeout",
    "verbose": "verbose",
    "parallel": "parallel",
    "workers": "workers",
    "report_format": "report_format",
    "report_output": "report_output",
    "update_snapshots": "update_snapshots",
    "filter_name": "filter_name",
    "filter_marker": "filter_marker",
}


def _merge_cli(
    file_kwargs: dict[str, Any],
    cli: Namespace,
) -> dict[str, Any]:
    """Overlay CLI flags on top of file-derived kwargs.  CLI wins."""
    merged = dict(file_kwargs)
    cli_dict = vars(cli) if cli else {}

    for cli_attr, cfg_field in _CLI_MAP.items():
        value = cli_dict.get(cli_attr)
        if value is not None:
            merged[cfg_field] = value

    # Positional test path overrides test_dirs when provided
    test_path = cli_dict.get("test_path")
    if test_path is not None:
        merged["test_dirs"] = [test_path] if isinstance(test_path, str) else list(test_path)

    return merged


# ---------------------------------------------------------------------------
# Public API: load_config
# ---------------------------------------------------------------------------


def load_config(cli_args: Namespace) -> HarnessConfig:
    """Load configuration from file + CLI flags.  CLI takes precedence.

    Auto-discovers ``mcp-test.yaml`` / ``mcp-test.toml`` in the current
    working directory when no ``--config`` flag is provided.

    Raises ``SystemExit(2)`` when no server command can be determined.
    """
    config_path: Path | None = None
    cli_dict = vars(cli_args) if cli_args else {}

    # Resolve config file path
    explicit = cli_dict.get("config")
    if explicit:
        config_path = Path(explicit)
    else:
        config_path = _discover_config_file()

    # Parse file (if any)
    file_kwargs: dict[str, Any] = {}
    if config_path is not None and config_path.is_file():
        raw = _parse_config_file(config_path)
        file_kwargs = _flatten_config(raw)

    # Merge CLI on top
    merged = _merge_cli(file_kwargs, cli_args)

    # server_command is required
    if "server_command" not in merged or not merged["server_command"]:
        import sys

        print(
            "Error: No server command specified. "
            "Provide --server-command or set server.command in a config file "
            "(mcp-test.yaml / mcp-test.toml).",
            file=sys.stderr,
        )
        raise SystemExit(2)

    return HarnessConfig(**merged)


# ---------------------------------------------------------------------------
# Public API: validate_config_file
# ---------------------------------------------------------------------------

_VALID_TRANSPORTS = {"stdio", "sse", "http"}
_VALID_REPORT_FORMATS = {"json", "junit"}


def _find_yaml_line(text: str, key: str) -> int | None:
    """Return the 1-based line number where *key* first appears in *text*."""
    for idx, line in enumerate(text.splitlines(), start=1):
        stripped = line.lstrip()
        if stripped.startswith(f"{key}:") or stripped.startswith(f"{key} :"):
            return idx
    return None


def validate_config_file(path: Path) -> list[ConfigError]:
    """Validate a config file against the known schema.

    Returns a list of :class:`ConfigError` instances.  Each error includes
    a ``line`` number when it can be determined (YAML only -- TOML line
    tracking is not supported by the stdlib parser).
    """
    errors: list[ConfigError] = []

    if not path.is_file():
        errors.append(ConfigError(f"Config file not found: {path}"))
        return errors

    suffix = path.suffix.lower()
    is_yaml = suffix in (".yaml", ".yml")

    try:
        raw = _parse_config_file(path)
    except Exception as exc:  # noqa: BLE001
        errors.append(ConfigError(f"Failed to parse config file: {exc}"))
        return errors

    text = path.read_text(encoding="utf-8") if is_yaml else ""

    # -- unknown top-level keys --
    for key in raw:
        if key not in _KNOWN_TOP_KEYS:
            line = _find_yaml_line(text, key) if is_yaml else None
            errors.append(ConfigError(f"Unknown top-level key: '{key}'", line=line))

    # -- server section --
    server = raw.get("server")
    if server is not None:
        if not isinstance(server, dict):
            line = _find_yaml_line(text, "server") if is_yaml else None
            errors.append(ConfigError("'server' must be a mapping", line=line))
        else:
            for key in server:
                if key not in _KNOWN_SERVER_KEYS:
                    line = _find_yaml_line(text, key) if is_yaml else None
                    errors.append(
                        ConfigError(f"Unknown key in server section: '{key}'", line=line)
                    )
            transport = server.get("transport")
            if transport is not None and transport not in _VALID_TRANSPORTS:
                line = _find_yaml_line(text, "transport") if is_yaml else None
                errors.append(
                    ConfigError(
                        f"Invalid transport '{transport}'. "
                        f"Must be one of: {', '.join(sorted(_VALID_TRANSPORTS))}",
                        line=line,
                    )
                )
            opts = server.get("transport_options")
            if opts is not None and not isinstance(opts, dict):
                line = _find_yaml_line(text, "transport_options") if is_yaml else None
                errors.append(
                    ConfigError("'transport_options' must be a mapping", line=line)
                )

    # -- test section --
    test = raw.get("test")
    if test is not None:
        if not isinstance(test, dict):
            line = _find_yaml_line(text, "test") if is_yaml else None
            errors.append(ConfigError("'test' must be a mapping", line=line))
        else:
            for key in test:
                if key not in _KNOWN_TEST_KEYS:
                    line = _find_yaml_line(text, key) if is_yaml else None
                    errors.append(
                        ConfigError(f"Unknown key in test section: '{key}'", line=line)
                    )
            timeout = test.get("timeout")
            if timeout is not None:
                try:
                    val = float(timeout)
                    if val <= 0:
                        raise ValueError  # noqa: TRY301
                except (TypeError, ValueError):
                    line = _find_yaml_line(text, "timeout") if is_yaml else None
                    errors.append(
                        ConfigError("'timeout' must be a positive number", line=line)
                    )
            workers = test.get("workers")
            if workers is not None:
                try:
                    val_w = int(workers)
                    if val_w <= 0:
                        raise ValueError  # noqa: TRY301
                except (TypeError, ValueError):
                    line = _find_yaml_line(text, "workers") if is_yaml else None
                    errors.append(
                        ConfigError("'workers' must be a positive integer", line=line)
                    )
            dirs = test.get("dirs")
            if dirs is not None and not isinstance(dirs, list):
                line = _find_yaml_line(text, "dirs") if is_yaml else None
                errors.append(ConfigError("'dirs' must be a list", line=line))

    # -- report section --
    report = raw.get("report")
    if report is not None:
        if not isinstance(report, dict):
            line = _find_yaml_line(text, "report") if is_yaml else None
            errors.append(ConfigError("'report' must be a mapping", line=line))
        else:
            for key in report:
                if key not in _KNOWN_REPORT_KEYS:
                    line = _find_yaml_line(text, key) if is_yaml else None
                    errors.append(
                        ConfigError(f"Unknown key in report section: '{key}'", line=line)
                    )
            fmt = report.get("format")
            if fmt is not None and fmt not in _VALID_REPORT_FORMATS:
                line = _find_yaml_line(text, "format") if is_yaml else None
                errors.append(
                    ConfigError(
                        f"Invalid report format '{fmt}'. "
                        f"Must be one of: {', '.join(sorted(_VALID_REPORT_FORMATS))}",
                        line=line,
                    )
                )

    # -- plugins --
    plugins = raw.get("plugins")
    if plugins is not None and not isinstance(plugins, list):
        line = _find_yaml_line(text, "plugins") if is_yaml else None
        errors.append(ConfigError("'plugins' must be a list", line=line))

    # -- schema_validation --
    sv = raw.get("schema_validation")
    if sv is not None and not isinstance(sv, bool):
        line = _find_yaml_line(text, "schema_validation") if is_yaml else None
        errors.append(ConfigError("'schema_validation' must be a boolean", line=line))

    return errors
