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
    except ImportError:  # pragma: no cover
        return False  # pragma: no cover


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

    def validate_initialize_result(self, init_result: Any) -> list[SchemaViolation]:
        """Validate the MCP ``initialize`` handshake result structure."""
        if not self._enabled:
            return []
        violations: list[SchemaViolation] = []
        if init_result is None:
            violations.append(
                SchemaViolation(
                    json_path="$.result",
                    expected_type="InitializeResult",
                    actual_value=None,
                    message="Initialize result is missing",
                )
            )
            return violations
        proto = _get(init_result, "protocolVersion", None)
        if proto is None or not isinstance(proto, (str, int)):
            violations.append(
                SchemaViolation(
                    json_path="$.protocolVersion",
                    expected_type="string | integer",
                    actual_value=proto,
                    message="Initialize result must include 'protocolVersion' (string or integer)",
                )
            )
        caps = _get(init_result, "capabilities", None)
        if caps is None:
            violations.append(
                SchemaViolation(
                    json_path="$.capabilities",
                    expected_type="object",
                    actual_value=None,
                    message="Initialize result must include 'capabilities'",
                )
            )
        sinfo = _get(init_result, "serverInfo", None)
        if sinfo is None:
            violations.append(
                SchemaViolation(
                    json_path="$.serverInfo",
                    expected_type="object",
                    actual_value=None,
                    message="Initialize result must include 'serverInfo'",
                )
            )
        elif isinstance(sinfo, dict):
            if "name" not in sinfo or not isinstance(sinfo.get("name"), str):
                violations.append(
                    SchemaViolation(
                        json_path="$.serverInfo.name",
                        expected_type="string",
                        actual_value=_get(sinfo, "name", None),
                        message="serverInfo must include string 'name'",
                    )
                )
        elif hasattr(sinfo, "name"):
            n = _get(sinfo, "name", None)
            if n is None or not isinstance(n, str):
                violations.append(
                    SchemaViolation(
                        json_path="$.serverInfo.name",
                        expected_type="string",
                        actual_value=n,
                        message="serverInfo must include string 'name'",
                    )
                )
        return violations

    def validate_list_tools_shape(self, tools: list[Any]) -> list[SchemaViolation]:
        """Validate each tool in ``tools/list`` has required MCP fields."""
        if not self._enabled:
            return []
        violations: list[SchemaViolation] = []
        for idx, tool in enumerate(tools):
            pfx = f"$.tools[{idx}]"
            name = _get(tool, "name", None)
            if not isinstance(name, str):
                violations.append(
                    SchemaViolation(
                        json_path=f"{pfx}.name",
                        expected_type="string (non-empty)",
                        actual_value=name,
                        message="Each tool must have a string 'name'",
                    )
                )
            desc = _get(tool, "description", None)
            if not isinstance(desc, str):
                violations.append(
                    SchemaViolation(
                        json_path=f"{pfx}.description",
                        expected_type="string",
                        actual_value=desc,
                        message="Each tool must include a string 'description' (may be empty)",
                    )
                )
            ischema = _get(tool, "inputSchema", None)
            if not isinstance(ischema, dict):
                violations.append(
                    SchemaViolation(
                        json_path=f"{pfx}.inputSchema",
                        expected_type="object (JSON Schema)",
                        actual_value=ischema,
                        message="Each tool must have an object 'inputSchema'",
                    )
                )
        return violations

    def validate_list_resources_shape(self, resources: list[Any]) -> list[SchemaViolation]:
        """Validate each resource in ``resources/list`` has required MCP fields."""
        if not self._enabled:
            return []
        violations: list[SchemaViolation] = []
        for idx, res in enumerate(resources):
            pfx = f"$.resources[{idx}]"
            uri = _get(res, "uri", None)
            if uri is None or not isinstance(uri, str):
                violations.append(
                    SchemaViolation(
                        json_path=f"{pfx}.uri",
                        expected_type="string",
                        actual_value=uri,
                        message="Each resource must have a string 'uri'",
                    )
                )
            name = _get(res, "name", None)
            if not isinstance(name, str):
                violations.append(
                    SchemaViolation(
                        json_path=f"{pfx}.name",
                        expected_type="string",
                        actual_value=name,
                        message="Each resource must have a string 'name'",
                    )
                )
            mt = _get(res, "mimeType", None)
            if mt is not None and not isinstance(mt, str):
                violations.append(
                    SchemaViolation(
                        json_path=f"{pfx}.mimeType",
                        expected_type="string | null",
                        actual_value=mt,
                        message="Resource 'mimeType' must be a string if present",
                    )
                )
        return violations

    def validate_list_prompts_shape(self, prompts: list[Any]) -> list[SchemaViolation]:
        """Validate each prompt in ``prompts/list`` has required MCP fields."""
        if not self._enabled:
            return []
        violations: list[SchemaViolation] = []
        for idx, pr in enumerate(prompts):
            pfx = f"$.prompts[{idx}]"
            name = _get(pr, "name", None)
            if not isinstance(name, str):
                violations.append(
                    SchemaViolation(
                        json_path=f"{pfx}.name",
                        expected_type="string",
                        actual_value=name,
                        message="Each prompt must have a string 'name'",
                    )
                )
            args = _get(pr, "arguments", None)
            if args is not None and not isinstance(args, list):
                violations.append(
                    SchemaViolation(
                        json_path=f"{pfx}.arguments",
                        expected_type="array | null",
                        actual_value=args,
                        message="Prompt 'arguments' must be an array if present",
                    )
                )
        return violations

    def validate_content_items_shape(self, items: list[Any]) -> list[SchemaViolation]:
        """Validate tool/prompt result content items (Text, Image, …)."""
        if not self._enabled:
            return []
        violations: list[SchemaViolation] = []
        for i, item in enumerate(items):
            pfx = f"$.content[{i}]"
            typ = _get(item, "type", None)
            if typ is None or not isinstance(typ, str):
                violations.append(
                    SchemaViolation(
                        json_path=f"{pfx}.type",
                        expected_type="string",
                        actual_value=typ,
                        message="Content item must include string 'type' (e.g. 'text', 'image')",
                    )
                )
                continue
            if typ == "text":
                if not isinstance(_get(item, "text", None), str):
                    violations.append(
                        SchemaViolation(
                            json_path=f"{pfx}.text",
                            expected_type="string",
                            actual_value=_get(item, "text", None),
                            message="TextContent requires string 'text'",
                        )
                    )
            elif typ == "image":
                if not isinstance(_get(item, "data", None), str):
                    violations.append(
                        SchemaViolation(
                            json_path=f"{pfx}.data",
                            expected_type="string (base64)",
                            actual_value=None,
                            message="ImageContent requires string 'data'",
                        )
                    )
                if not isinstance(_get(item, "mimeType", None), str):
                    violations.append(
                        SchemaViolation(
                            json_path=f"{pfx}.mimeType",
                            expected_type="string",
                            actual_value=_get(item, "mimeType", None),
                            message="ImageContent requires string 'mimeType'",
                        )
                    )
        return violations


async def validate_mcp_server_after_connect(
    session: Any,
    init_result: Any,
    validator: SchemaValidator,
    *,
    schema_probe_call_tool: bool = True,
) -> list[SchemaViolation]:
    """Run MCP shape checks and tool inputSchema validation after connect."""
    v: list[SchemaViolation] = []
    v.extend(validator.validate_initialize_result(init_result))
    tools: list[Any] = []
    try:
        lt = await session.list_tools()
        tools = getattr(lt, "tools", None) or []
        v.extend(validator.validate_list_tools_shape(tools))
        v.extend(validator.validate_tool_schemas(tools))
    except Exception as exc:  # noqa: BLE001
        v.append(
            SchemaViolation(
                json_path="$.list_tools",
                expected_type="ListToolsResult",
                actual_value=None,
                message=f"list_tools failed: {exc}",
            )
        )
        tools = []
    for call, name, shape_fn, attr in (
        (lambda: session.list_resources(), "list_resources", "validate_list_resources_shape", "resources"),
        (lambda: session.list_prompts(), "list_prompts", "validate_list_prompts_shape", "prompts"),
    ):
        try:
            res = await call()
        except Exception:
            continue
        items = getattr(res, attr, None) or []
        v.extend(getattr(validator, shape_fn)(items))

    # Best-effort: validate tool *result* content shapes once (first tool, empty args).
    if (
        schema_probe_call_tool
        and tools
        and not v
        and hasattr(session, "call_tool")
    ):
        tprobe = ""
        try:
            t0 = tools[0]
            tprobe = _get(t0, "name", None) or ""
            if isinstance(tprobe, str) and tprobe:
                ctr = await session.call_tool(tprobe, {})
                raw_items = getattr(ctr, "content", None) or []
                v.extend(validator.validate_content_items_shape(list(raw_items)))
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "Schema content probe (call_tool %r) skipped: %s",
                tprobe,
                exc,
            )
    return v


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
