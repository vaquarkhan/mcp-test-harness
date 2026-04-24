"""Extra config tests -- cover remaining validation branches."""

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


def _ns(**kwargs):
    defaults = {
        "server_command": None, "transport": None, "config": None,
        "timeout": None, "verbose": None, "parallel": None,
        "workers": None, "report_format": None, "report_output": None,
        "update_snapshots": None, "filter_name": None, "filter_marker": None,
        "test_path": None, "list": None, "watch": None,
    }
    defaults.update(kwargs)
    return Namespace(**defaults)


class TestValidateConfigFileExtraBranches:
    def test_server_not_mapping(self, tmp_path: Path):
        f = tmp_path / "mcp-test.yaml"
        f.write_text("server: just_a_string\n")
        errs = validate_config_file(f)
        assert any("mapping" in e.message for e in errs)

    def test_test_not_mapping(self, tmp_path: Path):
        f = tmp_path / "mcp-test.yaml"
        f.write_text("server:\n  command: srv\ntest: not_a_mapping\n")
        errs = validate_config_file(f)
        assert any("mapping" in e.message for e in errs)

    def test_report_not_mapping(self, tmp_path: Path):
        f = tmp_path / "mcp-test.yaml"
        f.write_text("server:\n  command: srv\nreport: not_a_mapping\n")
        errs = validate_config_file(f)
        assert any("mapping" in e.message for e in errs)

    def test_transport_options_not_mapping(self, tmp_path: Path):
        f = tmp_path / "mcp-test.yaml"
        f.write_text("server:\n  command: srv\n  transport_options: bad\n")
        errs = validate_config_file(f)
        assert any("transport_options" in e.message for e in errs)

    def test_dirs_not_list(self, tmp_path: Path):
        f = tmp_path / "mcp-test.yaml"
        f.write_text("server:\n  command: srv\ntest:\n  dirs: not_a_list\n")
        errs = validate_config_file(f)
        assert any("dirs" in e.message for e in errs)

    def test_unknown_report_key(self, tmp_path: Path):
        f = tmp_path / "mcp-test.yaml"
        f.write_text("server:\n  command: srv\nreport:\n  format: json\n  extra_key: bad\n")
        errs = validate_config_file(f)
        assert any("extra_key" in e.message for e in errs)

    def test_unknown_test_key(self, tmp_path: Path):
        f = tmp_path / "mcp-test.yaml"
        f.write_text("server:\n  command: srv\ntest:\n  unknown_key: bad\n")
        errs = validate_config_file(f)
        assert any("unknown_key" in e.message for e in errs)

    def test_parse_error(self, tmp_path: Path):
        f = tmp_path / "mcp-test.yaml"
        f.write_text(":\n  bad yaml {{{\n")
        errs = validate_config_file(f)
        assert any("parse" in e.message.lower() or "Failed" in e.message for e in errs)

    def test_unsupported_format(self, tmp_path: Path):
        f = tmp_path / "mcp-test.json"
        f.write_text('{"server": {"command": "srv"}}')
        errs = validate_config_file(f)
        assert any("Unsupported" in e.message or "parse" in e.message.lower() for e in errs)


class TestLoadConfigExtraBranches:
    def test_toml_config_loading(self, tmp_path: Path):
        f = tmp_path / "mcp-test.toml"
        # In TOML, top-level keys must come BEFORE any [section] headers
        lines = [
            'schema_validation = false',
            'plugins = ["my_plugin"]',
            '',
            '[server]',
            'command = "python srv.py"',
            'transport = "stdio"',
            '',
            '[test]',
            'dirs = ["integration/"]',
            'timeout = 45',
            'parallel = true',
            'workers = 2',
            '',
            '[report]',
            'format = "json"',
            'output = "out.json"',
        ]
        f.write_text("\n".join(lines) + "\n")
        ns = _ns(config=str(f))
        cfg = load_config(ns)
        assert cfg.server_command == "python srv.py"
        assert cfg.test_dirs == ["integration/"]
        assert cfg.timeout == 45.0
        assert cfg.parallel is True
        assert cfg.workers == 2
        assert cfg.report_format == "json"
        assert cfg.report_output == "out.json"
        assert cfg.plugins == ["my_plugin"]

    def test_empty_yaml_file(self, tmp_path: Path):
        f = tmp_path / "mcp-test.yaml"
        f.write_text("")
        ns = _ns(config=str(f), server_command="echo hi")
        cfg = load_config(ns)
        assert cfg.server_command == "echo hi"

    def test_non_dict_yaml_raises(self, tmp_path: Path):
        f = tmp_path / "mcp-test.yaml"
        f.write_text("- item1\n- item2\n")
        ns = _ns(config=str(f), server_command="echo hi")
        with pytest.raises(ValueError, match="mapping"):
            load_config(ns)
