"""Tests for the explicit allowlist of agent-visible tool definitions."""

import json

import pytest

from patty_bot.agent.tool_executor import _TOOL_HANDLERS
from patty_bot.agent.tool_registry import TOOL_REGISTRY, ToolDefinition, agent_tool_definitions, get_tool_definition


def test_registry_exposes_the_expected_domain_tools() -> None:
    assert tuple(tool.name for tool in TOOL_REGISTRY) == (
        "search_catalog",
        "recommend_products",
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


def test_recommendation_tool_schema_exposes_structured_optional_criteria() -> None:
    definition = get_tool_definition("recommend_products")

    assert definition is not None
    assert definition.input_schema["properties"] == {
        "category": {"type": "string", "minLength": 1},
        "servings": {"type": "integer", "minimum": 0},
        "excluded_allergens": {"type": "array", "items": {"type": "string", "minLength": 1}},
        "max_price": {"type": "string", "minLength": 1},
    }


def test_every_public_tool_has_a_private_handler() -> None:
    assert {tool.name for tool in TOOL_REGISTRY} <= set(_TOOL_HANDLERS)


def test_no_private_handler_exists_without_a_public_tool_definition() -> None:
    assert set(_TOOL_HANDLERS) <= {tool.name for tool in TOOL_REGISTRY}


def test_registry_returns_none_for_unknown_tools() -> None:
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
        )
