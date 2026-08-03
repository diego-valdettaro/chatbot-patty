"""Controlled server-side execution of registered agent tools."""

from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path
from typing import Callable, Mapping

from patty_bot.domain.cart import Cart
from patty_bot.tools.cart_tools import add_to_cart, change_cart_quantity, get_cart, remove_from_cart
from patty_bot.domain.catalog import Product
from patty_bot.tools.catalog_tools import search_catalog
from patty_bot.tools.recommendation_tools import recommend_products
from patty_bot.tools.order_tools import (
    confirm_order,
    get_order_summary,
    update_order_details,
    validate_order_details_tool,
)
from patty_bot.domain.orders import Order, OrderDetails
from patty_bot.agent.tool_registry import get_tool_definition
from patty_bot.agent.tool_contracts import JsonValue, ToolCall, ToolError, ToolResult, tool_failure


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


ToolHandler = Callable[[AgentSession, Mapping[str, JsonValue]], ToolExecution]


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

    handler = _TOOL_HANDLERS.get(tool_call.name)
    if handler is None:
        # The registry remains the allowlist; this guard identifies incomplete internal wiring.
        return _failed_execution(session, "unsupported_tool", "This tool has no executor handler.")
    return handler(session, _arguments_for_domain_tool(tool_call))


def _execute_search_catalog(session: AgentSession, arguments: Mapping[str, JsonValue]) -> ToolExecution:
    return ToolExecution(session=session, result=search_catalog(session.products, arguments))


def _execute_recommend_products(session: AgentSession, arguments: Mapping[str, JsonValue]) -> ToolExecution:
    return ToolExecution(session=session, result=recommend_products(session.products, arguments))


def _execute_get_cart(session: AgentSession, arguments: Mapping[str, JsonValue]) -> ToolExecution:
    del arguments
    return ToolExecution(session=session, result=get_cart(session.cart))


def _execute_add_to_cart(session: AgentSession, arguments: Mapping[str, JsonValue]) -> ToolExecution:
    execution = add_to_cart(session.cart, session.products, arguments)
    return ToolExecution(session=replace(session, cart=execution.cart), result=execution.result)


def _execute_change_cart_quantity(session: AgentSession, arguments: Mapping[str, JsonValue]) -> ToolExecution:
    execution = change_cart_quantity(session.cart, arguments)
    return ToolExecution(session=replace(session, cart=execution.cart), result=execution.result)


def _execute_remove_from_cart(session: AgentSession, arguments: Mapping[str, JsonValue]) -> ToolExecution:
    execution = remove_from_cart(session.cart, arguments)
    return ToolExecution(session=replace(session, cart=execution.cart), result=execution.result)


def _execute_update_order_details(session: AgentSession, arguments: Mapping[str, JsonValue]) -> ToolExecution:
    execution = update_order_details(session.order_details, arguments, session.reference_date)
    return ToolExecution(session=replace(session, order_details=execution.details), result=execution.result)


def _execute_validate_order_details(session: AgentSession, arguments: Mapping[str, JsonValue]) -> ToolExecution:
    del arguments
    return ToolExecution(
        session=session,
        result=validate_order_details_tool(session.order_details, session.reference_date),
    )


def _execute_get_order_summary(session: AgentSession, arguments: Mapping[str, JsonValue]) -> ToolExecution:
    del arguments
    return ToolExecution(
        session=session,
        result=get_order_summary(session.cart, session.order_details, session.reference_date),
    )


def _execute_confirm_order(session: AgentSession, arguments: Mapping[str, JsonValue]) -> ToolExecution:
    del arguments
    execution = confirm_order(
        session.database_path,
        session.cart,
        session.order_details,
        session.reference_date,
    )
    return ToolExecution(session=replace(session, confirmed_order=execution.order), result=execution.result)


_TOOL_HANDLERS: Mapping[str, ToolHandler] = {
    "search_catalog": _execute_search_catalog,
    "recommend_products": _execute_recommend_products,
    "get_cart": _execute_get_cart,
    "add_to_cart": _execute_add_to_cart,
    "change_cart_quantity": _execute_change_cart_quantity,
    "remove_from_cart": _execute_remove_from_cart,
    "update_order_details": _execute_update_order_details,
    "validate_order_details": _execute_validate_order_details,
    "get_order_summary": _execute_get_order_summary,
    "confirm_order": _execute_confirm_order,
}


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
