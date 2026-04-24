"""Tests for mcp_test_harness.config module."""

from __future__ import annotations

import logging
from argparse import Namespace
from pathlib import Path

import pytest

from mcp_test_harness.config import (
    ConfigError,
    HarnessConfig,
    load_config,
    validate_config_file,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ns(**kwargs: object) -> Namespace:
    """Build a CLI Namespace with sensible defaults (all None)."""
    defaults = {
        "server_command": None,
        "transport": None,
        "config": None,
        "timeout": None,
        "verbose": None,
        "parallel": None,
        "workers": None,
        "report_format": None,
        "report_output": None,
        "update_snapshots": None,
        "filter_name": None,
        "filter_marker": None,
        "test_path": None,
        "list": None,
        "watch": None,
    }
    defaults.update(kwargs)
    return Namespace(**defaults)


# ---------------------------------------------------------------------------
# HarnessConfig dataclass
# ---------------------------------------------------------------------------


class TestHarnessConfig:
    def test_frozen(self) -> None:
        cfg = HarnessConfig(server_command="echo hi")
        with pytest.raises(AttributeError):
            cfg.server_command = "nope"  # type: ignore[misc]

    def test_defaults(self) -> None:
        cfg = HarnessConfig(server_command="echo hi")
        assert cfg.transport == "stdio"
        assert cfg.timeout == 30.0
        assert cfg.test_dirs == ["tests/"]
        assert cfg.report_format is None
        assert cfg.parallel is False
        assert cfg.schema_validation is True
        assert cfg.verbose is False
        assert cfg.update_snapshots is False


# ---------------------------------------------------------------------------
# load_config -- YAML
# ---------------------------------------------------------------------------


class TestLoadConfigYAML:
    def test_yaml_basic(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "mcp-test.yaml"
        cfg_file.write_text(
            "server:\n  command: python server.py\n  transport: sse\n"
        )
        ns = _ns(config=str(cfg_file))
        cfg = load_config(ns)
        assert cfg.server_command == "python server.py"
        assert cfg.transport == "sse"

    def test_yaml_all_sections(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "mcp-test.yaml"
        cfg_file.write_text(
            "server:\n"
            "  command: node srv.js\n"
            "  transport: http\n"
            "  transport_options:\n"
            "    host: localhost\n"
            "    port: 9090\n"
            "test:\n"
            "  dirs:\n"
            "    - integration/\n"
            "  timeout: 60\n"
            "  parallel: true\n"
            "  workers: 8\n"
            "report:\n"
            "  format: junit\n"
            "  output: out.xml\n"
            "schema_validation: false\n"
            "plugins:\n"
            "  - my_plugin\n"
        )
        ns = _ns(config=str(cfg_file))
        cfg = load_config(ns)
        assert cfg.server_command == "node srv.js"
        assert cfg.transport == "http"
        assert cfg.transport_options == {"host": "localhost", "port": 9090}
        assert cfg.test_dirs == ["integration/"]
        assert cfg.timeout == 60.0
        assert cfg.parallel is True
        assert cfg.workers == 8
        assert cfg.report_format == "junit"
        assert cfg.report_output == "out.xml"
        assert cfg.schema_validation is False
        assert cfg.plugins == ["my_plugin"]


# ---------------------------------------------------------------------------
# load_config -- TOML
# ---------------------------------------------------------------------------


class TestLoadConfigTOML:
    def test_toml_basic(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "mcp-test.toml"
        cfg_file.write_text(
            '[server]\ncommand = "python server.py"\ntransport = "stdio"\n'
        )
        ns = _ns(config=str(cfg_file))
        cfg = load_config(ns)
        assert cfg.server_command == "python server.py"
        assert cfg.transport == "stdio"


# ---------------------------------------------------------------------------
# load_config -- CLI override precedence
# ---------------------------------------------------------------------------


class TestCLIPrecedence:
    def test_cli_overrides_file(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "mcp-test.yaml"
        cfg_file.write_text(
            "server:\n  command: from-file\n  transport: sse\ntest:\n  timeout: 10\n"
        )
        ns = _ns(
            config=str(cfg_file),
            server_command="from-cli",
            transport="http",
            timeout=99.0,
        )
        cfg = load_config(ns)
        assert cfg.server_command == "from-cli"
        assert cfg.transport == "http"
        assert cfg.timeout == 99.0

    def test_cli_only_no_file(self) -> None:
        ns = _ns(server_command="echo hi", transport="stdio")
        cfg = load_config(ns)
        assert cfg.server_command == "echo hi"

    def test_test_path_overrides_dirs(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "mcp-test.yaml"
        cfg_file.write_text("server:\n  command: srv\ntest:\n  dirs:\n    - a/\n")
        ns = _ns(config=str(cfg_file), test_path="my_tests/")
        cfg = load_config(ns)
        assert cfg.test_dirs == ["my_tests/"]


# ---------------------------------------------------------------------------
# load_config -- missing server command -> exit code 2
# ---------------------------------------------------------------------------


class TestMissingServerCommand:
    def test_no_config_no_cli_exits_2(self) -> None:
        ns = _ns()
        with pytest.raises(SystemExit) as exc_info:
            load_config(ns)
        assert exc_info.value.code == 2


# ---------------------------------------------------------------------------
# Auto-discovery
# ---------------------------------------------------------------------------


class TestAutoDiscovery:
    def test_discovers_yaml(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        (tmp_path / "mcp-test.yaml").write_text("server:\n  command: auto-yaml\n")
        monkeypatch.chdir(tmp_path)
        ns = _ns()
        cfg = load_config(ns)
        assert cfg.server_command == "auto-yaml"

    def test_discovers_toml(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        (tmp_path / "mcp-test.toml").write_text('[server]\ncommand = "auto-toml"\n')
        monkeypatch.chdir(tmp_path)
        ns = _ns()
        cfg = load_config(ns)
        assert cfg.server_command == "auto-toml"

    def test_yaml_preferred_over_toml(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (tmp_path / "mcp-test.yaml").write_text("server:\n  command: yaml-wins\n")
        (tmp_path / "mcp-test.toml").write_text('[server]\ncommand = "toml-loses"\n')
        monkeypatch.chdir(tmp_path)
        ns = _ns()
        cfg = load_config(ns)
        assert cfg.server_command == "yaml-wins"


# ---------------------------------------------------------------------------
# Unknown keys -> warnings
# ---------------------------------------------------------------------------


class TestUnknownKeyWarnings:
    def test_unknown_top_key_warns(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        cfg_file = tmp_path / "mcp-test.yaml"
        cfg_file.write_text("server:\n  command: srv\nfoo_bar: 123\n")
        ns = _ns(config=str(cfg_file))
        with caplog.at_level(logging.WARNING):
            load_config(ns)
        assert any("foo_bar" in r.message for r in caplog.records)

    def test_unknown_server_key_warns(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        cfg_file = tmp_path / "mcp-test.yaml"
        cfg_file.write_text("server:\n  command: srv\n  magic: true\n")
        ns = _ns(config=str(cfg_file))
        with caplog.at_level(logging.WARNING):
            load_config(ns)
        assert any("magic" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# validate_config_file
# ---------------------------------------------------------------------------


class TestValidateConfigFile:
    def test_valid_yaml_no_errors(self, tmp_path: Path) -> None:
        f = tmp_path / "mcp-test.yaml"
        f.write_text(
            "server:\n"
            "  command: python srv.py\n"
            "  transport: stdio\n"
            "test:\n"
            "  timeout: 30\n"
            "schema_validation: true\n"
        )
        assert validate_config_file(f) == []

    def test_missing_file(self, tmp_path: Path) -> None:
        errs = validate_config_file(tmp_path / "nope.yaml")
        assert len(errs) == 1
        assert "not found" in errs[0].message

    def test_invalid_transport(self, tmp_path: Path) -> None:
        f = tmp_path / "mcp-test.yaml"
        f.write_text("server:\n  command: srv\n  transport: websocket\n")
        errs = validate_config_file(f)
        assert any("transport" in e.message.lower() for e in errs)

    def test_invalid_report_format(self, tmp_path: Path) -> None:
        f = tmp_path / "mcp-test.yaml"
        f.write_text("server:\n  command: srv\nreport:\n  format: csv\n")
        errs = validate_config_file(f)
        assert any("format" in e.message.lower() for e in errs)

    def test_unknown_top_key_reported(self, tmp_path: Path) -> None:
        f = tmp_path / "mcp-test.yaml"
        f.write_text("server:\n  command: srv\nfoo: 1\n")
        errs = validate_config_file(f)
        assert any("foo" in e.message for e in errs)

    def test_line_numbers_in_yaml(self, tmp_path: Path) -> None:
        f = tmp_path / "mcp-test.yaml"
        f.write_text("server:\n  command: srv\n  transport: bad\n")
        errs = validate_config_file(f)
        transport_errs = [e for e in errs if "transport" in e.message.lower()]
        assert transport_errs
        assert transport_errs[0].line is not None
        assert transport_errs[0].line == 3  # "  transport: bad" is line 3

    def test_negative_timeout(self, tmp_path: Path) -> None:
        f = tmp_path / "mcp-test.yaml"
        f.write_text("server:\n  command: srv\ntest:\n  timeout: -5\n")
        errs = validate_config_file(f)
        assert any("timeout" in e.message for e in errs)

    def test_negative_workers(self, tmp_path: Path) -> None:
        f = tmp_path / "mcp-test.yaml"
        f.write_text("server:\n  command: srv\ntest:\n  workers: 0\n")
        errs = validate_config_file(f)
        assert any("workers" in e.message for e in errs)

    def test_plugins_not_list(self, tmp_path: Path) -> None:
        f = tmp_path / "mcp-test.yaml"
        f.write_text("server:\n  command: srv\nplugins: not_a_list\n")
        errs = validate_config_file(f)
        assert any("plugins" in e.message for e in errs)

    def test_schema_validation_not_bool(self, tmp_path: Path) -> None:
        f = tmp_path / "mcp-test.yaml"
        f.write_text("server:\n  command: srv\nschema_validation: yes_please\n")
        errs = validate_config_file(f)
        assert any("schema_validation" in e.message for e in errs)

    def test_validate_schema_each_worker_not_bool(self, tmp_path: Path) -> None:
        f = tmp_path / "mcp-test.yaml"
        f.write_text(
            "server:\n  command: srv\n"
            "validate_schema_each_parallel_worker: 1\n"
        )
        errs = validate_config_file(f)
        assert any("validate_schema_each_parallel_worker" in e.message for e in errs)

    def test_schema_probe_call_tool_not_bool(self, tmp_path: Path) -> None:
        f = tmp_path / "mcp-test.yaml"
        f.write_text("server:\n  command: srv\nschema_probe_call_tool: 2\n")
        errs = validate_config_file(f)
        assert any("schema_probe_call_tool" in e.message for e in errs)

    def test_toml_validation(self, tmp_path: Path) -> None:
        f = tmp_path / "mcp-test.toml"
        f.write_text(
            '[server]\ncommand = "srv"\ntransport = "bad"\n'
        )
        errs = validate_config_file(f)
        assert any("transport" in e.message.lower() for e in errs)
        # TOML errors won't have line numbers
        transport_errs = [e for e in errs if "transport" in e.message.lower()]
        assert transport_errs[0].line is None


# ---------------------------------------------------------------------------
# Environment variable expansion
# ---------------------------------------------------------------------------

import os

from mcp_test_harness.config import _expand_env_vars


class TestExpandEnvVars:
    def test_simple_string_replacement(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MY_CMD", "python server.py")
        assert _expand_env_vars("${MY_CMD}") == "python server.py"

    def test_missing_var_becomes_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("NONEXISTENT_VAR_XYZ", raising=False)
        assert _expand_env_vars("${NONEXISTENT_VAR_XYZ}") == ""

    def test_partial_replacement(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HOST", "localhost")
        assert _expand_env_vars("http://${HOST}:8080") == "http://localhost:8080"

    def test_multiple_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("A", "hello")
        monkeypatch.setenv("B", "world")
        assert _expand_env_vars("${A} ${B}") == "hello world"

    def test_dict_recursion(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CMD", "srv")
        data = {"server": {"command": "${CMD}"}, "other": 42}
        result = _expand_env_vars(data)
        assert result == {"server": {"command": "srv"}, "other": 42}

    def test_list_recursion(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DIR", "integration/")
        data = ["${DIR}", "unit/"]
        result = _expand_env_vars(data)
        assert result == ["integration/", "unit/"]

    def test_non_string_passthrough(self) -> None:
        assert _expand_env_vars(42) == 42
        assert _expand_env_vars(True) is True
        assert _expand_env_vars(None) is None

    def test_load_config_expands_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("TEST_SERVER_CMD", "python my_server.py")
        cfg_file = tmp_path / "mcp-test.yaml"
        cfg_file.write_text("server:\n  command: ${TEST_SERVER_CMD}\n")
        ns = _ns(config=str(cfg_file))
        cfg = load_config(ns)
        assert cfg.server_command == "python my_server.py"
