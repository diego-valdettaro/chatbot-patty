"""Tests for controlled execution against session-owned domain state."""

from datetime import date
from pathlib import Path

from patty_bot.domain.catalog import load_catalog
from patty_bot.tools.order_tools import OrderConfirmationToolExecution
from patty_bot.domain.orders import OrderDetails, create_confirmed_order
from patty_bot.agent import tool_executor
from patty_bot.agent.tool_executor import AgentSession, execute_tool_call
from patty_bot.agent.tool_contracts import ToolCall, tool_success


REFERENCE_DATE = date(2026, 7, 25)


def session() -> AgentSession:
    return AgentSession(
        products=load_catalog(Path("data/catalog.sample.csv")),
        database_path=Path("data/test-order.sqlite3"),
        reference_date=REFERENCE_DATE,
    )


def test_executor_uses_the_allowlist_and_keeps_session_on_unknown_tool() -> None:
    original = session()

    execution = execute_tool_call(original, ToolCall(name="delete_database"))

    assert execution.session is original
    assert execution.result.to_dict()["errors"][0]["code"] == "unknown_tool"


def test_executor_runs_recommendations_as_a_read_only_tool() -> None:
    original = session()

    execution = execute_tool_call(
        original,
        ToolCall(
            name="recommend_products",
            arguments={
                "category": "Tortas",
                "servings": 10,
                "excluded_allergens": [],
                "max_price": "100.00",
            },
        ),
    )

    assert execution.session is original
    assert execution.result.ok is True
    assert execution.result.to_dict()["data"]["recommendations"]


def test_executor_persists_cart_state_between_allowed_calls() -> None:
    added = execute_tool_call(
        session(), ToolCall(name="add_to_cart", arguments={"product_id": "brownie-chocolate-belga"})
    )
    summary = execute_tool_call(added.session, ToolCall(name="get_cart"))

    assert added.session.cart.items[0].product.id == "brownie-chocolate-belga"
    assert summary.result.to_dict()["data"]["subtotal"] == "8.00"


def test_executor_interprets_strict_nulls_as_unchanged_optional_order_fields() -> None:
    initial = session()
    call = ToolCall(
        name="update_order_details",
        arguments={
            "customer_name": "Diego",
            "customer_phone": None,
            "fulfillment_type": None,
            "requested_date": None,
            "delivery_address": None,
            "pickup_store": None,
        },
    )

    execution = execute_tool_call(initial, call)

    assert execution.session.order_details == OrderDetails(customer_name="Diego")
    assert execution.result.ok is True


def test_executor_blocks_confirmation_without_explicit_customer_action() -> None:
    original = session()

    execution = execute_tool_call(original, ToolCall(name="confirm_order"))

    assert execution.session is original
    assert execution.result.to_dict()["errors"][0]["code"] == "confirmation_required"


def test_executor_keeps_confirmed_order_server_side_and_locks_later_calls(monkeypatch) -> None:
    initial = session()
    added = execute_tool_call(
        initial, ToolCall(name="add_to_cart", arguments={"product_id": "brownie-chocolate-belga"})
    )
    ready = execute_tool_call(
        added.session,
        ToolCall(
            name="update_order_details",
            arguments={
                "customer_name": "Diego",
                "customer_phone": "999888777",
                "fulfillment_type": "delivery",
                "requested_date": "2026-07-27",
                "delivery_address": "Av. Siempre Viva 123",
                "pickup_store": None,
            },
        ),
    )
    confirmed_order = create_confirmed_order(
        ready.session.cart, ready.session.order_details, reference_date=REFERENCE_DATE
    )

    def fake_confirm_order(*_args, **_kwargs):
        return OrderConfirmationToolExecution(result=tool_success({"confirmed": True}), order=confirmed_order)

    monkeypatch.setattr("patty_bot.agent.tool_executor.confirm_order", fake_confirm_order)
    confirmed = execute_tool_call(
        ready.session, ToolCall(name="confirm_order"), explicit_confirmation=True
    )
    later_call = execute_tool_call(confirmed.session, ToolCall(name="get_cart"))

    assert confirmed.session.confirmed_order is confirmed_order
    assert confirmed.result.to_dict()["data"] == {"confirmed": True}
    assert later_call.session is confirmed.session
    assert later_call.result.to_dict()["errors"][0]["code"] == "order_already_confirmed"


def test_executor_translates_unexpected_tool_failures_and_preserves_the_session(monkeypatch) -> None:
    original = session()

    def failing_handler(*_args, **_kwargs):
        raise RuntimeError("database password and customer address")

    monkeypatch.setitem(tool_executor._TOOL_HANDLERS, "get_cart", failing_handler)
    execution = execute_tool_call(original, ToolCall(name="get_cart"))

    assert execution.session is original
    assert execution.result.to_dict() == {
        "ok": False,
        "data": {},
        "errors": [
            {
                "code": "tool_execution_failure",
                "message": "The requested action could not be completed.",
            }
        ],
    }
