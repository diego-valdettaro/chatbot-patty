from dataclasses import dataclass
from typing import Mapping

from patty_bot.tools import JsonValue


@dataclass(frozen=True)
class ToolDefinition:
    """A provider-neutral description of one operation the agent may request."""

    name: str
    description: str
    input_schema: Mapping[str, JsonValue]
    handler: str
    requires_explicit_confirmation: bool = False

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Tool definition name cannot be empty.")
        if not self.description.strip():
            raise ValueError("Tool definition description cannot be empty.")
        if not self.handler.strip():
            raise ValueError("Tool definition handler cannot be empty.")
        if not isinstance(self.input_schema, Mapping) or self.input_schema.get("type") != "object":
            raise ValueError("Tool definition input schema must describe an object.")

    def to_dict(self) -> dict[str, JsonValue]:
        """Return the JSON-serializable metadata consumed by a future agent provider."""

        return {
            "name": self.name,
            "description": self.description,
            "input_schema": dict(self.input_schema),
            "handler": self.handler,
            "requires_explicit_confirmation": self.requires_explicit_confirmation,
        }


# The registry is an allowlist. The future agent executor must not call functions outside it.
TOOL_REGISTRY: tuple[ToolDefinition, ...] = (
    ToolDefinition(
        name="search_catalog",
        description="Search active Patty catalog products by name, alias, category, or a close spelling.",
        input_schema={
            "type": "object",
            "properties": {"query": {"type": "string", "minLength": 1}},
            "required": ["query"],
            "additionalProperties": False,
        },
        handler="patty_bot.catalog_tools.search_catalog",
    ),
    ToolDefinition(
        name="get_cart",
        description="Return the current editable cart and its subtotal.",
        input_schema={"type": "object", "properties": {}, "additionalProperties": False},
        handler="patty_bot.cart_tools.get_cart",
    ),
    ToolDefinition(
        name="add_to_cart",
        description="Add one unit of an active catalog product to the editable cart.",
        input_schema={
            "type": "object",
            "properties": {"product_id": {"type": "string", "minLength": 1}},
            "required": ["product_id"],
            "additionalProperties": False,
        },
        handler="patty_bot.cart_tools.add_to_cart",
    ),
    ToolDefinition(
        name="change_cart_quantity",
        description="Set the quantity of an existing cart item.",
        input_schema={
            "type": "object",
            "properties": {
                "product_id": {"type": "string", "minLength": 1},
                "quantity": {"type": "integer", "minimum": 1},
            },
            "required": ["product_id", "quantity"],
            "additionalProperties": False,
        },
        handler="patty_bot.cart_tools.change_cart_quantity",
    ),
    ToolDefinition(
        name="remove_from_cart",
        description="Remove an existing item from the editable cart.",
        input_schema={
            "type": "object",
            "properties": {"product_id": {"type": "string", "minLength": 1}},
            "required": ["product_id"],
            "additionalProperties": False,
        },
        handler="patty_bot.cart_tools.remove_from_cart",
    ),
    ToolDefinition(
        name="update_order_details",
        description="Update customer, fulfillment, and requested-date details for the current draft order.",
        input_schema={
            "type": "object",
            "properties": {
                "customer_name": {"type": "string"},
                "customer_phone": {"type": "string"},
                "fulfillment_type": {"type": "string", "enum": ["delivery", "pickup"]},
                "requested_date": {
                    "anyOf": [{"type": "string", "format": "date"}, {"type": "null"}]
                },
                "delivery_address": {"type": "string"},
                "pickup_store": {"type": "string"},
            },
            "additionalProperties": False,
        },
        handler="patty_bot.order_tools.update_order_details",
    ),
    ToolDefinition(
        name="validate_order_details",
        description="Report missing or invalid fields for the current draft order.",
        input_schema={"type": "object", "properties": {}, "additionalProperties": False},
        handler="patty_bot.order_tools.validate_order_details_tool",
    ),
    ToolDefinition(
        name="get_order_summary",
        description="Return subtotal, delivery fee, total, and validation for the current draft order.",
        input_schema={"type": "object", "properties": {}, "additionalProperties": False},
        handler="patty_bot.order_tools.get_order_summary",
    ),
    ToolDefinition(
        name="confirm_order",
        description="Persist the current valid order only after an explicit customer confirmation action.",
        input_schema={"type": "object", "properties": {}, "additionalProperties": False},
        handler="patty_bot.order_tools.confirm_order",
        requires_explicit_confirmation=True,
    ),
)


def get_tool_definition(name: str) -> ToolDefinition | None:
    """Look up a tool by its public name without exposing arbitrary application functions."""

    return next((tool for tool in TOOL_REGISTRY if tool.name == name), None)


def agent_tool_definitions() -> tuple[dict[str, JsonValue], ...]:
    """Return every allowed tool as serializable metadata for an LLM provider adapter."""

    return tuple(tool.to_dict() for tool in TOOL_REGISTRY)
