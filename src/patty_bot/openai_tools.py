"""Adapt the provider-neutral tool registry to OpenAI function definitions."""

from collections.abc import Mapping
from copy import deepcopy

from patty_bot.tool_registry import TOOL_REGISTRY, ToolDefinition
from patty_bot.tools import JsonValue


def openai_tool_definitions() -> tuple[dict[str, JsonValue], ...]:
    """Return the allowlisted tools in the OpenAI Responses API function format.

    The registry remains the source of truth. This adapter does not expose
    handlers or confirmation metadata to the provider.
    """

    return tuple(openai_tool_definition(tool) for tool in TOOL_REGISTRY)


def openai_tool_definition(tool: ToolDefinition) -> dict[str, JsonValue]:
    """Translate one registry entry into a strict OpenAI function definition."""

    return {
        "type": "function",
        "name": tool.name,
        "description": tool.description,
        "parameters": _make_strict_schema(tool.input_schema),
        "strict": True,
    }


def _make_strict_schema(schema: Mapping[str, JsonValue]) -> dict[str, JsonValue]:
    """Copy a JSON schema and make object properties compatible with strict mode."""

    normalized = deepcopy(dict(schema))
    _normalize_schema_node(normalized)
    return normalized


def _normalize_schema_node(node: dict[str, JsonValue]) -> None:
    for keyword in ("anyOf", "oneOf", "allOf"):
        options = node.get(keyword)
        if isinstance(options, list):
            for option in options:
                if isinstance(option, dict):
                    _normalize_schema_node(option)

    properties = node.get("properties")
    if node.get("type") != "object" or not isinstance(properties, dict):
        return

    original_required = set(node.get("required", []))
    normalized_properties: dict[str, JsonValue] = {}
    for name, property_schema in properties.items():
        if not isinstance(property_schema, dict):
            raise ValueError(f"Property schema for {name!r} must be a JSON object.")

        normalized_property = deepcopy(property_schema)
        _normalize_schema_node(normalized_property)
        if name not in original_required and not _allows_null(normalized_property):
            normalized_property = {"anyOf": [normalized_property, {"type": "null"}]}
        normalized_properties[name] = normalized_property

    # Strict mode requires every declared field and forbids extra keys.
    node["properties"] = normalized_properties
    node["required"] = list(normalized_properties)
    node["additionalProperties"] = False


def _allows_null(schema: Mapping[str, JsonValue]) -> bool:
    schema_type = schema.get("type")
    if schema_type == "null" or (isinstance(schema_type, list) and "null" in schema_type):
        return True

    options = schema.get("anyOf")
    return isinstance(options, list) and any(
        isinstance(option, dict) and _allows_null(option) for option in options
    )
