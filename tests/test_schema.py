"""Tests for mcp_test_harness.schema -- SchemaValidator."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import pytest

from mcp_test_harness.models import SchemaViolation
from mcp_test_harness.schema import SchemaValidator, _template_to_regex


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@dataclass
class FakeTool:
    name: str
    inputSchema: dict[str, Any]


@dataclass
class FakeResource:
    uri: str


@dataclass
class FakeTemplate:
    uriTemplate: str


# ---------------------------------------------------------------------------
# validate_response -- valid cases
# ---------------------------------------------------------------------------


class TestValidateResponseValid:
    def test_valid_result_response(self) -> None:
        v = SchemaValidator(enabled=True)
        resp = {"jsonrpc": "2.0", "id": 1, "result": {"ok": True}}
        assert v.validate_response(resp) == []

    def test_valid_error_response(self) -> None:
        v = SchemaValidator(enabled=True)
        resp = {
            "jsonrpc": "2.0",
            "id": "abc",
            "error": {"code": -32600, "message": "Invalid Request"},
        }
        assert v.validate_response(resp) == []

    def test_null_id_is_valid(self) -> None:
        v = SchemaValidator(enabled=True)
        resp = {"jsonrpc": "2.0", "id": None, "result": []}
        assert v.validate_response(resp) == []

    def test_string_id_is_valid(self) -> None:
        v = SchemaValidator(enabled=True)
        resp = {"jsonrpc": "2.0", "id": "req-42", "result": "done"}
        assert v.validate_response(resp) == []


# ---------------------------------------------------------------------------
# validate_response -- invalid cases
# ---------------------------------------------------------------------------


class TestValidateResponseInvalid:
    def test_missing_jsonrpc(self) -> None:
        v = SchemaValidator()
        violations = v.validate_response({"id": 1, "result": {}})
        assert any("jsonrpc" in viol.message for viol in violations)

    def test_wrong_jsonrpc_version(self) -> None:
        v = SchemaValidator()
        violations = v.validate_response({"jsonrpc": "1.0", "id": 1, "result": {}})
        assert any("2.0" in viol.message for viol in violations)

    def test_missing_id(self) -> None:
        v = SchemaValidator()
        violations = v.validate_response({"jsonrpc": "2.0", "result": {}})
        assert any("id" in viol.json_path for viol in violations)

    def test_invalid_id_type(self) -> None:
        v = SchemaValidator()
        violations = v.validate_response({"jsonrpc": "2.0", "id": [1], "result": {}})
        assert any("id" in viol.json_path for viol in violations)

    def test_missing_result_and_error(self) -> None:
        v = SchemaValidator()
        violations = v.validate_response({"jsonrpc": "2.0", "id": 1})
        assert any("result" in viol.message or "error" in viol.message for viol in violations)

    def test_both_result_and_error(self) -> None:
        v = SchemaValidator()
        resp = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {},
            "error": {"code": -1, "message": "oops"},
        }
        violations = v.validate_response(resp)
        assert any("both" in viol.message.lower() for viol in violations)

    def test_error_not_object(self) -> None:
        v = SchemaValidator()
        violations = v.validate_response({"jsonrpc": "2.0", "id": 1, "error": "bad"})
        assert any("error" in viol.json_path for viol in violations)

    def test_error_missing_code(self) -> None:
        v = SchemaValidator()
        resp = {"jsonrpc": "2.0", "id": 1, "error": {"message": "oops"}}
        violations = v.validate_response(resp)
        assert any("code" in viol.json_path for viol in violations)

    def test_error_missing_message(self) -> None:
        v = SchemaValidator()
        resp = {"jsonrpc": "2.0", "id": 1, "error": {"code": -1}}
        violations = v.validate_response(resp)
        assert any("message" in viol.json_path for viol in violations)

    def test_error_code_wrong_type(self) -> None:
        v = SchemaValidator()
        resp = {"jsonrpc": "2.0", "id": 1, "error": {"code": "NaN", "message": "x"}}
        violations = v.validate_response(resp)
        assert any("code" in viol.json_path for viol in violations)

    def test_non_dict_response(self) -> None:
        v = SchemaValidator()
        violations = v.validate_response("not a dict")  # type: ignore[arg-type]
        assert len(violations) == 1
        assert violations[0].json_path == "$"

    def test_violations_have_json_path(self) -> None:
        """Every violation must carry a json_path."""
        v = SchemaValidator()
        violations = v.validate_response({})
        assert all(isinstance(viol.json_path, str) for viol in violations)
        assert len(violations) > 0


# ---------------------------------------------------------------------------
# validate_tool_schemas
# ---------------------------------------------------------------------------


class TestValidateToolSchemas:
    def test_valid_tool_schema(self) -> None:
        v = SchemaValidator()
        tools = [
            FakeTool(
                name="echo",
                inputSchema={"type": "object", "properties": {"msg": {"type": "string"}}},
            )
        ]
        assert v.validate_tool_schemas(tools) == []

    def test_missing_input_schema(self) -> None:
        v = SchemaValidator()
        # Use a dict without inputSchema
        tools = [{"name": "broken"}]
        violations = v.validate_tool_schemas(tools)
        assert any("inputSchema" in viol.message for viol in violations)

    def test_invalid_json_schema(self) -> None:
        v = SchemaValidator()
        tools = [
            FakeTool(
                name="bad",
                inputSchema={"type": "not-a-real-type"},
            )
        ]
        violations = v.validate_tool_schemas(tools)
        assert any("bad" in viol.message for viol in violations)

    def test_non_dict_input_schema(self) -> None:
        v = SchemaValidator()
        tools = [FakeTool(name="x", inputSchema="nope")]  # type: ignore[arg-type]
        violations = v.validate_tool_schemas(tools)
        assert any("inputSchema" in viol.json_path for viol in violations)

    def test_dict_style_tools(self) -> None:
        """Tools passed as plain dicts should also work."""
        v = SchemaValidator()
        tools = [
            {"name": "add", "inputSchema": {"type": "object", "properties": {"a": {"type": "number"}}}},
        ]
        assert v.validate_tool_schemas(tools) == []

    def test_missing_name(self) -> None:
        v = SchemaValidator()
        tools = [{"inputSchema": {"type": "object"}}]
        violations = v.validate_tool_schemas(tools)
        assert any("name" in viol.json_path for viol in violations)


# ---------------------------------------------------------------------------
# validate_resource_uris
# ---------------------------------------------------------------------------


class TestValidateResourceUris:
    def test_matching_uri(self) -> None:
        v = SchemaValidator()
        resources = [FakeResource(uri="file:///docs/readme.md")]
        templates = [FakeTemplate(uriTemplate="file:///docs/{filename}")]
        assert v.validate_resource_uris(resources, templates) == []

    def test_non_matching_uri(self) -> None:
        v = SchemaValidator()
        resources = [FakeResource(uri="http://other/path")]
        templates = [FakeTemplate(uriTemplate="file:///docs/{filename}")]
        violations = v.validate_resource_uris(resources, templates)
        assert len(violations) == 1
        assert "does not match" in violations[0].message

    def test_no_templates_means_no_violations(self) -> None:
        v = SchemaValidator()
        resources = [FakeResource(uri="anything://goes")]
        assert v.validate_resource_uris(resources, []) == []

    def test_multiple_templates(self) -> None:
        v = SchemaValidator()
        resources = [FakeResource(uri="db://users/42")]
        templates = [
            FakeTemplate(uriTemplate="file:///{path}"),
            FakeTemplate(uriTemplate="db://users/{id}"),
        ]
        assert v.validate_resource_uris(resources, templates) == []

    def test_dict_style_resources_and_templates(self) -> None:
        v = SchemaValidator()
        resources = [{"uri": "s3://bucket/key"}]
        templates = [{"uriTemplate": "s3://bucket/{key}"}]
        assert v.validate_resource_uris(resources, templates) == []

    def test_missing_uri(self) -> None:
        v = SchemaValidator()
        resources = [{"name": "no-uri"}]
        templates = [FakeTemplate(uriTemplate="x://{y}")]
        violations = v.validate_resource_uris(resources, templates)
        assert any("uri" in viol.json_path for viol in violations)


# ---------------------------------------------------------------------------
# Disabled validation
# ---------------------------------------------------------------------------


class TestDisabledValidation:
    def test_disabled_validate_response_returns_empty(self, caplog: pytest.LogCaptureFixture) -> None:
        v = SchemaValidator(enabled=False)
        with caplog.at_level(logging.WARNING):
            result = v.validate_response({"garbage": True})
        assert result == []
        assert any("disabled" in r.message.lower() for r in caplog.records)

    def test_disabled_validate_tool_schemas_returns_empty(self) -> None:
        v = SchemaValidator(enabled=False)
        assert v.validate_tool_schemas([{"bad": True}]) == []

    def test_disabled_validate_resource_uris_returns_empty(self) -> None:
        v = SchemaValidator(enabled=False)
        assert v.validate_resource_uris([{"uri": "x"}], [{"uriTemplate": "y://{z}"}]) == []

    def test_disabled_logs_warning_on_init(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.WARNING):
            SchemaValidator(enabled=False)
        assert any("disabled" in r.message.lower() for r in caplog.records)


# ---------------------------------------------------------------------------
# URI template regex helper
# ---------------------------------------------------------------------------


class TestTemplateToRegex:
    def test_simple_variable(self) -> None:
        pat = _template_to_regex("file:///{name}")
        assert pat.match("file:///readme.md")
        assert not pat.match("file:///")

    def test_multiple_variables(self) -> None:
        pat = _template_to_regex("db://{schema}/{table}")
        assert pat.match("db://public/users")
        assert not pat.match("db://public/users/extra")

    def test_literal_only(self) -> None:
        pat = _template_to_regex("http://localhost:8080/health")
        assert pat.match("http://localhost:8080/health")
        assert not pat.match("http://localhost:8080/other")
