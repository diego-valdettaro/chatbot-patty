"""Tests for the OpenAI function-calling adapter."""

import json

from patty_bot.openai_tools import openai_tool_definition, openai_tool_definitions
from patty_bot.tool_registry import ToolDefinition


def test_adapter_publishes_only_openai_function_metadata() -> None:
    definitions = openai_tool_definitions()

    assert tuple(definition["name"] for definition in definitions) == (
        "search_catalog",
        "get_cart",
        "add_to_cart",
        "change_cart_quantity",
        "remove_from_cart",
        "update_order_details",
        "validate_order_details",
        "get_order_summary",
        "confirm_order",
    )
    assert all(definition["type"] == "function" for definition in definitions)
    assert all(definition["strict"] is True for definition in definitions)
    assert all("handler" not in definition for definition in definitions)
    assert all("requires_explicit_confirmation" not in definition for definition in definitions)
    assert json.loads(json.dumps(definitions)) == list(definitions)


def test_adapter_makes_optional_arguments_nullable_and_required_for_strict_mode() -> None:
    details_tool = next(
        definition for definition in openai_tool_definitions() if definition["name"] == "update_order_details"
    )
    parameters = details_tool["parameters"]

    assert parameters["required"] == [
        "customer_name",
        "customer_phone",
        "fulfillment_type",
        "requested_date",
        "delivery_address",
        "pickup_store",
    ]
    assert parameters["additionalProperties"] is False
    assert parameters["properties"]["customer_name"] == {
        "anyOf": [{"type": "string"}, {"type": "null"}]
    }
    assert parameters["properties"]["requested_date"] == {
        "anyOf": [{"type": "string", "format": "date"}, {"type": "null"}]
    }


def test_adapter_preserves_required_arguments_without_making_them_nullable() -> None:
    search_tool = next(
        definition for definition in openai_tool_definitions() if definition["name"] == "search_catalog"
    )

    assert search_tool["parameters"] == {
        "type": "object",
        "properties": {"query": {"type": "string", "minLength": 1}},
        "required": ["query"],
        "additionalProperties": False,
    }


def test_adapter_normalizes_nested_object_properties() -> None:
    definition = ToolDefinition(
        name="nested",
        description="Nested schema test.",
        input_schema={
            "type": "object",
            "properties": {
                "address": {
                    "type": "object",
                    "properties": {"street": {"type": "string"}},
                    "additionalProperties": False,
                }
            },
            "additionalProperties": False,
        },
        handler="patty_bot.tests.nested",
    )

    parameters = openai_tool_definition(definition)["parameters"]

    assert parameters["required"] == ["address"]
    assert parameters["properties"]["address"] == {
        "anyOf": [
            {
                "type": "object",
                "properties": {
                    "street": {"anyOf": [{"type": "string"}, {"type": "null"}]}
                },
                "required": ["street"],
                "additionalProperties": False,
            },
            {"type": "null"},
        ]
    }
