import sqlite3
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path
from typing import Mapping

from patty_bot.domain.cart import Cart
from patty_bot.domain.orders import ORDER_STATUS_PENDING, Order, OrderDetails, OrderValidationResult, delivery_fee_for_order, total_for_order, validate_order_details
from patty_bot.infrastructure.repository import save_confirmed_order
from patty_bot.agent.tool_contracts import JsonValue, ToolError, ToolResult, tool_failure, tool_success


@dataclass(frozen=True)
class OrderDetailsToolExecution:
    """An order-details tool result and the server-side details after the operation."""

    details: OrderDetails
    result: ToolResult


@dataclass(frozen=True)
class OrderConfirmationToolExecution:
    """A confirmation result and the internal confirmed order when persistence succeeds."""

    result: ToolResult
    order: Order | None = None


def update_order_details(
    details: OrderDetails,
    arguments: Mapping[str, JsonValue],
    reference_date: date | None = None,
) -> OrderDetailsToolExecution:
    # Keep the tool contract strict: unknown fields usually indicate an agent/schema mismatch.
    unsupported_fields = set(arguments) - {
        "customer_name",
        "customer_phone",
        "fulfillment_type",
        "requested_date",
        "delivery_address",
        "pickup_store",
    }
    if unsupported_fields:
        field = sorted(unsupported_fields)[0]
        return _failed_details_execution(details, "Unsupported order detail field.", field)

    # Validate JSON types at the tool boundary before constructing the domain model.
    string_fields = ("customer_name", "customer_phone", "delivery_address", "pickup_store")
    for field in string_fields:
        if field in arguments and not isinstance(arguments[field], str):
            return _failed_details_execution(details, f"{field} must be a string.", field)

    # Only the supported modes can be persisted or used for pricing.
    fulfillment_type = arguments.get("fulfillment_type", details.fulfillment_type)
    if not isinstance(fulfillment_type, str) or fulfillment_type not in {"delivery", "pickup"}:
        return _failed_details_execution(
            details,
            "fulfillment_type must be delivery or pickup.",
            "fulfillment_type",
        )

    # Dates cross the tool boundary as ISO strings; null explicitly clears a previous date.
    requested_date = details.requested_date
    if "requested_date" in arguments:
        requested_date_value = arguments["requested_date"]
        if requested_date_value is None:
            requested_date = None
        elif isinstance(requested_date_value, str):
            try:
                requested_date = date.fromisoformat(requested_date_value)
            except ValueError:
                return _failed_details_execution(
                    details,
                    "requested_date must use YYYY-MM-DD format.",
                    "requested_date",
                )
        else:
            return _failed_details_execution(details, "requested_date must be a string.", "requested_date")

    # Preserve omitted fields so the agent can collect details incrementally across several turns.
    updated_details = replace(
        details,
        customer_name=arguments.get("customer_name", details.customer_name),
        customer_phone=arguments.get("customer_phone", details.customer_phone),
        fulfillment_type=fulfillment_type,
        requested_date=requested_date,
        delivery_address=arguments.get("delivery_address", details.delivery_address),
        pickup_store=arguments.get("pickup_store", details.pickup_store),
    )
    # Return server-side state plus a serializable validation snapshot for the next agent decision.
    return OrderDetailsToolExecution(
        details=updated_details,
        result=tool_success(_details_payload(updated_details, reference_date)),
    )


def validate_order_details_tool(
    details: OrderDetails,
    reference_date: date | None = None,
) -> ToolResult:
    return tool_success(_details_payload(details, reference_date))


def get_order_summary(
    cart: Cart,
    details: OrderDetails,
    reference_date: date | None = None,
) -> ToolResult:
    # A summary is still useful while incomplete; validation tells the agent what remains to collect.
    validation = validate_order_details(details, reference_date=reference_date)
    return tool_success(
        {
            "subtotal": f"{cart.subtotal:.2f}",
            "delivery_fee": f"{delivery_fee_for_order(details):.2f}",
            "total": f"{total_for_order(cart, details):.2f}",
            "validation": _serialize_validation(validation),
        }
    )


def confirm_order(
    database_path: str | Path,
    cart: Cart,
    details: OrderDetails,
    reference_date: date | None = None,
) -> OrderConfirmationToolExecution:
    # Perform domain validation before persistence so the tool never creates a partial order.
    errors = _confirm_order_errors(cart, details, reference_date)
    if errors:
        return OrderConfirmationToolExecution(result=tool_failure(*errors))

    # Do not expose database details to the agent; return a recoverable persistence error instead.
    try:
        confirmed_order = save_confirmed_order(database_path, cart, details, reference_date=reference_date)
    except (OSError, sqlite3.Error):
        return OrderConfirmationToolExecution(
            result=tool_failure(
                ToolError(code="persistence_failure", message="The order could not be saved. Please try again.")
            )
        )

    return OrderConfirmationToolExecution(
        # The aggregate remains server-side; neither its internal ID nor customer data are sent to the agent.
        order=confirmed_order,
        result=tool_success({"confirmed": True, "status": ORDER_STATUS_PENDING}),
    )


def _details_payload(details: OrderDetails, reference_date: date | None) -> dict[str, JsonValue]:
    validation = validate_order_details(details, reference_date=reference_date)
    return {
        "order_details": {
            "customer_name": details.customer_name,
            "customer_phone": details.customer_phone,
            "fulfillment_type": details.fulfillment_type,
            "requested_date": details.requested_date.isoformat() if details.requested_date else None,
            "delivery_address": details.delivery_address,
            "pickup_store": details.pickup_store,
        },
        "validation": _serialize_validation(validation),
    }


def _serialize_validation(validation: OrderValidationResult) -> dict[str, JsonValue]:
    return {
        "is_valid": validation.is_valid,
        "missing_fields": list(validation.missing_fields),
        "invalid_fields": list(validation.invalid_fields),
    }


def _failed_details_execution(details: OrderDetails, message: str, field: str) -> OrderDetailsToolExecution:
    return OrderDetailsToolExecution(
        details=details,
        result=tool_failure(ToolError(code="invalid_argument", message=message, field=field)),
    )


def _confirm_order_errors(
    cart: Cart,
    details: OrderDetails,
    reference_date: date | None,
) -> tuple[ToolError, ...]:
    errors: list[ToolError] = []
    if cart.is_empty:
        errors.append(ToolError(code="empty_cart", message="The cart cannot be empty."))

    validation = validate_order_details(details, reference_date=reference_date)
    errors.extend(
        ToolError(code="missing_required_field", message="A required field is missing.", field=field)
        for field in validation.missing_fields
    )
    errors.extend(
        ToolError(code="invalid_field", message="A field has an invalid value.", field=field)
        for field in validation.invalid_fields
    )
    return tuple(errors)
