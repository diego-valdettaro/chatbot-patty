"""Controlled server-side execution of registered agent tools."""

from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path
from typing import Mapping

from patty_bot.cart import Cart
from patty_bot.cart_tools import add_to_cart, change_cart_quantity, get_cart, remove_from_cart
from patty_bot.catalog import Product
from patty_bot.catalog_tools import search_catalog
from patty_bot.order_tools import (
    confirm_order,
    get_order_summary,
    update_order_details,
    validate_order_details_tool,
)
from patty_bot.orders import Order, OrderDetails
from patty_bot.tool_registry import get_tool_definition
from patty_bot.tools import JsonValue, ToolCall, ToolError, ToolResult, tool_failure


@dataclass(frozen=True)
class AgentSession:
    """Server-owned domain state used while an agent handles one customer session."""

    products: tuple[Product, ...]
    database_path: Path
    cart: Cart = Cart()
    order_details: OrderDetails = OrderDetails()
    confirmed_order: Order | None = None
    reference_date: date | None = None


@dataclass(frozen=True)
class ToolExecution:
    """A controlled tool response plus the resulting server-side session state."""

    session: AgentSession
    result: ToolResult


def execute_tool_call(
    session: AgentSession,
    tool_call: ToolCall,
    *,
    explicit_confirmation: bool = False,
) -> ToolExecution:
    """Execute one allowlisted call without giving the agent direct domain access."""

    definition = get_tool_definition(tool_call.name)
    if definition is None:
        return _failed_execution(session, "unknown_tool", "This tool is not available.")

    if session.confirmed_order is not None:
        return _failed_execution(
            session,
            "order_already_confirmed",
            "The confirmed order cannot be changed.",
        )

    if definition.requires_explicit_confirmation and not explicit_confirmation:
        return _failed_execution(
            session,
            "confirmation_required",
            "Order confirmation requires an explicit customer action.",
        )

    arguments = _arguments_for_domain_tool(tool_call)
    if tool_call.name == "search_catalog":
        return ToolExecution(session=session, result=search_catalog(session.products, arguments))
    if tool_call.name == "get_cart":
        return ToolExecution(session=session, result=get_cart(session.cart))
    if tool_call.name == "add_to_cart":
        execution = add_to_cart(session.cart, session.products, arguments)
        return ToolExecution(session=replace(session, cart=execution.cart), result=execution.result)
    if tool_call.name == "change_cart_quantity":
        execution = change_cart_quantity(session.cart, arguments)
        return ToolExecution(session=replace(session, cart=execution.cart), result=execution.result)
    if tool_call.name == "remove_from_cart":
        execution = remove_from_cart(session.cart, arguments)
        return ToolExecution(session=replace(session, cart=execution.cart), result=execution.result)
    if tool_call.name == "update_order_details":
        execution = update_order_details(session.order_details, arguments, session.reference_date)
        return ToolExecution(session=replace(session, order_details=execution.details), result=execution.result)
    if tool_call.name == "validate_order_details":
        return ToolExecution(
            session=session,
            result=validate_order_details_tool(session.order_details, session.reference_date),
        )
    if tool_call.name == "get_order_summary":
        return ToolExecution(
            session=session,
            result=get_order_summary(session.cart, session.order_details, session.reference_date),
        )
    if tool_call.name == "confirm_order":
        execution = confirm_order(
            session.database_path,
            session.cart,
            session.order_details,
            session.reference_date,
        )
        return ToolExecution(session=replace(session, confirmed_order=execution.order), result=execution.result)

    # The registry lookup above is the allowlist; this is a guard for future registry additions.
    return _failed_execution(session, "unsupported_tool", "This tool has no executor handler.")


def _arguments_for_domain_tool(tool_call: ToolCall) -> Mapping[str, JsonValue]:
    """Restore omitted optional fields after OpenAI strict-mode serialization."""

    if tool_call.name != "update_order_details":
        return tool_call.arguments

    # Strict schemas require fields to be present. Null carries "no change" for text and mode
    # fields, while requested_date keeps its existing domain meaning: clear the date explicitly.
    return {
        name: value
        for name, value in tool_call.arguments.items()
        if value is not None or name == "requested_date"
    }


def _failed_execution(session: AgentSession, code: str, message: str) -> ToolExecution:
    return ToolExecution(session=session, result=tool_failure(ToolError(code=code, message=message)))
