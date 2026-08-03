from dataclasses import dataclass
from typing import Mapping

from patty_bot.agent.tool_contracts import JsonValue


@dataclass(frozen=True)
class ToolDefinition:
    """A provider-neutral description of one operation the agent may request."""

    name: str
    description: str
    input_schema: Mapping[str, JsonValue]
    requires_explicit_confirmation: bool = False

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Tool definition name cannot be empty.")
        if not self.description.strip():
            raise ValueError("Tool definition description cannot be empty.")
        if not isinstance(self.input_schema, Mapping) or self.input_schema.get("type") != "object":
            raise ValueError("Tool definition input schema must describe an object.")

    def to_dict(self) -> dict[str, JsonValue]:
        """Return the JSON-serializable metadata consumed by a future agent provider."""

        return {
            "name": self.name,
            "description": self.description,
            "input_schema": dict(self.input_schema),
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
    ),
    ToolDefinition(
        name="recommend_products",
        description=(
            "Recommend compatible catalog products when the customer describes needs or asks for help choosing; "
            "use search_catalog when they know a product name, alias, or category."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "category": {"type": "string", "minLength": 1},
                "servings": {"type": "integer", "minimum": 0},
                "excluded_allergens": {"type": "array", "items": {"type": "string", "minLength": 1}},
                "max_price": {"type": "string", "minLength": 1},
            },
            "additionalProperties": False,
        },
    ),
    ToolDefinition(
        name="get_cart",
        description="Return the current editable cart and its subtotal.",
        input_schema={"type": "object", "properties": {}, "additionalProperties": False},
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
    ),
    ToolDefinition(
        name="validate_order_details",
        description="Report missing or invalid fields for the current draft order.",
        input_schema={"type": "object", "properties": {}, "additionalProperties": False},
    ),
    ToolDefinition(
        name="get_order_summary",
        description="Return subtotal, delivery fee, total, and validation for the current draft order.",
        input_schema={"type": "object", "properties": {}, "additionalProperties": False},
    ),
    ToolDefinition(
        name="confirm_order",
        description="Persist the current valid order only after an explicit customer confirmation action.",
        input_schema={"type": "object", "properties": {}, "additionalProperties": False},
        requires_explicit_confirmation=True,
    ),
)


def get_tool_definition(name: str) -> ToolDefinition | None:
    """Look up a tool by its public name without exposing arbitrary application functions."""

    return next((tool for tool in TOOL_REGISTRY if tool.name == name), None)


def agent_tool_definitions() -> tuple[dict[str, JsonValue], ...]:
    """Return every allowed tool as serializable metadata for an LLM provider adapter."""

    return tuple(tool.to_dict() for tool in TOOL_REGISTRY)
