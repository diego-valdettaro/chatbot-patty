"""Tests for the explicit allowlist of agent-visible tool definitions."""

import json

import pytest

from patty_bot.tool_registry import TOOL_REGISTRY, ToolDefinition, agent_tool_definitions, get_tool_definition


def test_registry_exposes_the_expected_domain_tools() -> None:
    assert tuple(tool.name for tool in TOOL_REGISTRY) == (
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


def test_registry_schemas_are_json_serializable_and_disallow_unknown_arguments() -> None:
    definitions = agent_tool_definitions()

    assert json.loads(json.dumps(definitions)) == list(definitions)
    assert all(definition["input_schema"]["type"] == "object" for definition in definitions)
    assert all(definition["input_schema"]["additionalProperties"] is False for definition in definitions)


def test_registry_maps_public_tools_to_their_explicit_handlers() -> None:
    search_tool = get_tool_definition("search_catalog")
    validation_tool = get_tool_definition("validate_order_details")

    assert search_tool is not None
    assert search_tool.handler == "patty_bot.catalog_tools.search_catalog"
    assert validation_tool is not None
    assert validation_tool.handler == "patty_bot.order_tools.validate_order_details_tool"
    assert get_tool_definition("unknown_tool") is None


def test_only_order_confirmation_requires_an_explicit_customer_action() -> None:
    confirmation_tools = tuple(
        tool.name for tool in TOOL_REGISTRY if tool.requires_explicit_confirmation
    )

    assert confirmation_tools == ("confirm_order",)


def test_tool_definition_rejects_a_schema_that_does_not_describe_an_object() -> None:
    with pytest.raises(ValueError, match="must describe an object"):
        ToolDefinition(
            name="invalid",
            description="Invalid schema example.",
            input_schema={"type": "string"},
            handler="patty_bot.invalid",
        )
