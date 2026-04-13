"""Schema validation for MCP JSON-RPC responses, tool schemas, and resource URIs.

Validates structural correctness of MCP messages against the JSON-RPC 2.0
envelope format, checks that tool input schemas are valid JSON Schema, and
verifies resource URIs match declared URI templates (RFC 6570 basic level).

Requirements: 4.1, 4.2, 4.3, 4.4, 4.5
"""

from __future__ import annotations

import logging
import re
from typing import Any

from mcp_test_harness.models import SchemaViolation

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Inline JSON-RPC 2.0 / MCP envelope schema (no external files needed)
# ---------------------------------------------------------------------------

# Required fields and their expected types for a JSON-RPC 2.0 response.
# Notifications (no "id") and requests are out of scope for response
# validation -- we focus on what the server sends back.
_JSONRPC_VERSION = "2.0"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _type_name(value: Any) -> str:
    """Return a human-friendly type name for *value*."""
    if value is None:
        return "null"
    return type(value).__name__


def _check_jsonschema_available() -> bool:
    """Return True if the ``jsonschema`` package is importable."""
    try:
        import jsonschema as _jsonschema  # noqa: F401
        return True
    except ImportError:
        return False


# ---------------------------------------------------------------------------
# URI template matching (RFC 6570 -- basic / Level 1 only)
# ---------------------------------------------------------------------------

# Level-1 templates contain simple variable expansions: {var}
_URI_TEMPLATE_VAR_RE = re.compile(r"\{([^}]+)\}")


def _template_to_regex(template: str) -> re.Pattern[str]:
    """Convert an RFC 6570 Level-1 URI template to a regex pattern.

    Each ``{variable}`` is replaced with a pattern that matches one or more
    non-``/`` characters.  Literal segments are escaped.
    """
    parts: list[str] = []
    last_end = 0
    for m in _URI_TEMPLATE_VAR_RE.finditer(template):
        # Escape the literal text between variables
        parts.append(re.escape(template[last_end : m.start()]))
        # Variable placeholder -- match non-empty, non-slash segment
        parts.append(r"[^/]+")
        last_end = m.end()
    parts.append(re.escape(template[last_end:]))
    return re.compile("^" + "".join(parts) + "$")


# ---------------------------------------------------------------------------
# SchemaValidator
# ---------------------------------------------------------------------------


class SchemaValidator:
    """Validates MCP JSON-RPC responses, tool schemas, and resource URIs.

    When *enabled* is ``False`` all public methods log a warning and return
    an empty violation list, satisfying requirement 4.5.
    """

    def __init__(self, enabled: bool = True) -> None:
        self._enabled = enabled
        self._has_jsonschema = _check_jsonschema_available()

        if not self._enabled:
            logger.warning(
                "Schema validation is disabled. MCP responses will NOT be "
                "checked for protocol conformance."
            )

    # -- public API ---------------------------------------------------------

    def validate_response(self, response: dict[str, Any]) -> list[SchemaViolation]:
        """Validate a JSON-RPC 2.0 response envelope.

        Checks:
        * ``jsonrpc`` field is present and equals ``"2.0"``
        * ``id`` field is present and is ``str | int | None``
        * Exactly one of ``result`` or ``error`` is present
        * If ``error`` is present it has ``code`` (int) and ``message`` (str)

        Returns a list of :class:`SchemaViolation` instances (empty on success).
        """
        if not self._enabled:
            logger.warning("Schema validation skipped (disabled).")
            return []

        violations: list[SchemaViolation] = []

        if not isinstance(response, dict):
            violations.append(
                SchemaViolation(
                    json_path="$",
                    expected_type="object",
                    actual_value=response,
                    message="Response must be a JSON object",
                )
            )
            return violations

        # -- jsonrpc field --
        if "jsonrpc" not in response:
            violations.append(
                SchemaViolation(
                    json_path="$.jsonrpc",
                    expected_type="string",
                    actual_value=None,
                    message="Missing required field 'jsonrpc'",
                )
            )
        else:
            jrpc = response["jsonrpc"]
            if jrpc != _JSONRPC_VERSION:
                violations.append(
                    SchemaViolation(
                        json_path="$.jsonrpc",
                        expected_type=f'"{_JSONRPC_VERSION}"',
                        actual_value=jrpc,
                        message=f"'jsonrpc' must be \"{_JSONRPC_VERSION}\", got \"{jrpc}\"",
                    )
                )

        # -- id field --
        if "id" not in response:
            violations.append(
                SchemaViolation(
                    json_path="$.id",
                    expected_type="string | integer | null",
                    actual_value=None,
                    message="Missing required field 'id'",
                )
            )
        else:
            id_val = response["id"]
            if id_val is not None and not isinstance(id_val, (str, int)):
                violations.append(
                    SchemaViolation(
                        json_path="$.id",
                        expected_type="string | integer | null",
                        actual_value=id_val,
                        message=f"'id' must be string, integer, or null; got {_type_name(id_val)}",
                    )
                )

        # -- result / error mutual exclusivity --
        has_result = "result" in response
        has_error = "error" in response

        if not has_result and not has_error:
            violations.append(
                SchemaViolation(
                    json_path="$",
                    expected_type="result | error",
                    actual_value=None,
                    message="Response must contain either 'result' or 'error'",
                )
            )
        elif has_result and has_error:
            violations.append(
                SchemaViolation(
                    json_path="$",
                    expected_type="result XOR error",
                    actual_value={"result": response["result"], "error": response["error"]},
                    message="Response must not contain both 'result' and 'error'",
                )
            )

        # -- error object structure --
        if has_error:
            err = response["error"]
            if not isinstance(err, dict):
                violations.append(
                    SchemaViolation(
                        json_path="$.error",
                        expected_type="object",
                        actual_value=err,
                        message="'error' must be a JSON object",
                    )
                )
            else:
                if "code" not in err:
                    violations.append(
                        SchemaViolation(
                            json_path="$.error.code",
                            expected_type="integer",
                            actual_value=None,
                            message="Error object missing required field 'code'",
                        )
                    )
                elif not isinstance(err["code"], int):
                    violations.append(
                        SchemaViolation(
                            json_path="$.error.code",
                            expected_type="integer",
                            actual_value=err["code"],
                            message=f"'error.code' must be integer; got {_type_name(err['code'])}",
                        )
                    )

                if "message" not in err:
                    violations.append(
                        SchemaViolation(
                            json_path="$.error.message",
                            expected_type="string",
                            actual_value=None,
                            message="Error object missing required field 'message'",
                        )
                    )
                elif not isinstance(err["message"], str):
                    violations.append(
                        SchemaViolation(
                            json_path="$.error.message",
                            expected_type="string",
                            actual_value=err["message"],
                            message=f"'error.message' must be string; got {_type_name(err['message'])}",
                        )
                    )

        return violations

    # -----------------------------------------------------------------------

    def validate_tool_schemas(self, tools: list[Any]) -> list[SchemaViolation]:
        """Validate that each tool's ``inputSchema`` is a valid JSON Schema.

        *tools* should be a list of objects with at least ``name`` (str) and
        ``inputSchema`` (dict) attributes or keys.

        When the ``jsonschema`` library is available the input schemas are
        checked with ``jsonschema.validators.validator_for`` /
        ``check_schema``.  Otherwise a lightweight structural check is
        performed (must be a dict with ``"type"`` key).
        """
        if not self._enabled:
            logger.warning("Schema validation skipped (disabled).")
            return []

        violations: list[SchemaViolation] = []

        for idx, tool in enumerate(tools):
            # Support both dict-like and attribute access
            name = _get(tool, "name", None)
            input_schema = _get(tool, "inputSchema", None)

            path_prefix = f"$.tools[{idx}]"
            display_name = name if isinstance(name, str) else f"tools[{idx}]"

            if name is None or not isinstance(name, str):
                violations.append(
                    SchemaViolation(
                        json_path=f"{path_prefix}.name",
                        expected_type="string",
                        actual_value=name,
                        message=f"Tool at index {idx} missing or invalid 'name'",
                    )
                )

            if input_schema is None:
                violations.append(
                    SchemaViolation(
                        json_path=f"{path_prefix}.inputSchema",
                        expected_type="object (JSON Schema)",
                        actual_value=None,
                        message=f"Tool '{display_name}' missing 'inputSchema'",
                    )
                )
                continue

            if not isinstance(input_schema, dict):
                violations.append(
                    SchemaViolation(
                        json_path=f"{path_prefix}.inputSchema",
                        expected_type="object (JSON Schema)",
                        actual_value=input_schema,
                        message=f"Tool '{display_name}' inputSchema must be a JSON object",
                    )
                )
                continue

            # Validate the schema itself
            if self._has_jsonschema:
                violations.extend(
                    self._validate_schema_with_jsonschema(input_schema, display_name, path_prefix)
                )
            else:
                violations.extend(
                    self._validate_schema_basic(input_schema, display_name, path_prefix)
                )

        return violations

    # -----------------------------------------------------------------------

    def validate_resource_uris(
        self,
        resources: list[Any],
        templates: list[Any],
    ) -> list[SchemaViolation]:
        """Validate resource URIs against declared URI templates.

        *resources* -- list of objects with a ``uri`` attribute/key.
        *templates* -- list of objects with a ``uriTemplate`` attribute/key.

        Each resource URI is tested against every template.  If templates
        are declared and a resource URI matches none of them, a violation
        is reported.
        """
        if not self._enabled:
            logger.warning("Schema validation skipped (disabled).")
            return []

        violations: list[SchemaViolation] = []

        # Compile templates
        compiled: list[tuple[str, re.Pattern[str]]] = []
        for t in templates:
            raw_template = _get(t, "uriTemplate", None)
            if raw_template and isinstance(raw_template, str):
                try:
                    compiled.append((raw_template, _template_to_regex(raw_template)))
                except re.error:
                    # If the template itself is malformed, skip it
                    logger.warning("Could not compile URI template: %s", raw_template)

        # If no templates declared, nothing to validate against
        if not compiled:
            return violations

        for idx, resource in enumerate(resources):
            uri = _get(resource, "uri", None)
            path_prefix = f"$.resources[{idx}]"

            if uri is None or not isinstance(uri, str):
                violations.append(
                    SchemaViolation(
                        json_path=f"{path_prefix}.uri",
                        expected_type="string",
                        actual_value=uri,
                        message=f"Resource at index {idx} missing or invalid 'uri'",
                    )
                )
                continue

            matched = any(pattern.match(uri) for _, pattern in compiled)
            if not matched:
                template_strs = [t for t, _ in compiled]
                violations.append(
                    SchemaViolation(
                        json_path=f"{path_prefix}.uri",
                        expected_type=f"URI matching one of: {template_strs}",
                        actual_value=uri,
                        message=(
                            f"Resource URI '{uri}' does not match any declared "
                            f"URI template: {template_strs}"
                        ),
                    )
                )

        return violations

    # -- private helpers ----------------------------------------------------

    def _validate_schema_with_jsonschema(
        self,
        schema: dict[str, Any],
        tool_name: str,
        path_prefix: str,
    ) -> list[SchemaViolation]:
        """Use the ``jsonschema`` library to validate a JSON Schema document."""
        import jsonschema

        violations: list[SchemaViolation] = []
        try:
            validator_cls = jsonschema.validators.validator_for(schema)
            validator_cls.check_schema(schema)
        except jsonschema.SchemaError as exc:
            violations.append(
                SchemaViolation(
                    json_path=f"{path_prefix}.inputSchema",
                    expected_type="valid JSON Schema",
                    actual_value=str(exc.message),
                    message=f"Tool '{tool_name}' has invalid inputSchema: {exc.message}",
                )
            )
        return violations

    def _validate_schema_basic(
        self,
        schema: dict[str, Any],
        tool_name: str,
        path_prefix: str,
    ) -> list[SchemaViolation]:
        """Lightweight fallback validation when ``jsonschema`` is not installed."""
        violations: list[SchemaViolation] = []
        if "type" not in schema:
            violations.append(
                SchemaViolation(
                    json_path=f"{path_prefix}.inputSchema.type",
                    expected_type="string",
                    actual_value=None,
                    message=(
                        f"Tool '{tool_name}' inputSchema missing 'type' field "
                        "(install jsonschema for full validation)"
                    ),
                )
            )
        return violations


# ---------------------------------------------------------------------------
# Attribute / key access helper
# ---------------------------------------------------------------------------


def _get(obj: Any, key: str, default: Any = None) -> Any:
    """Get a value from *obj* by attribute or key lookup."""
    # Try attribute access first (for dataclass / SDK objects)
    try:
        return getattr(obj, key)
    except AttributeError:
        pass
    # Fall back to dict-style access
    try:
        return obj[key]
    except (KeyError, TypeError, IndexError):
        pass
    return default
