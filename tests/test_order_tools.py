"""Tool-boundary tests for order updates, summaries, validation, and confirmation."""

from datetime import date
from pathlib import Path

from patty_bot.cart import Cart, add_product_to_cart
from patty_bot.catalog import load_catalog
from patty_bot.order_tools import (
    confirm_order,
    get_order_summary,
    update_order_details,
    validate_order_details_tool,
)
from patty_bot.orders import OrderDetails
from patty_bot.repository import ORDER_STATUS_PENDING


CATALOG_SAMPLE_PATH = Path("data/catalog.sample.csv")
REFERENCE_DATE = date(2026, 7, 25)


def valid_delivery_details() -> OrderDetails:
    return OrderDetails(
        customer_name="Diego Valdettaro",
        customer_phone="999888777",
        fulfillment_type="delivery",
        requested_date=date(2026, 7, 27),
        delivery_address="Av. Siempre Viva 123",
    )


def cart_with_brownie() -> Cart:
    return add_product_to_cart(Cart(), load_catalog(CATALOG_SAMPLE_PATH), "brownie-chocolate-belga")


def test_update_order_details_updates_server_state_and_reports_remaining_fields() -> None:
    execution = update_order_details(
        OrderDetails(),
        {"customer_name": "Diego", "fulfillment_type": "pickup", "pickup_store": "Benavides"},
        reference_date=REFERENCE_DATE,
    )

    assert execution.details.customer_name == "Diego"
    assert execution.details.fulfillment_type == "pickup"
    assert execution.details.pickup_store == "Benavides"
    assert execution.result.to_dict()["data"]["validation"] == {
        "is_valid": False,
        "missing_fields": ["customer_phone", "requested_date"],
        "invalid_fields": [],
    }


def test_update_order_details_rejects_bad_date_without_changing_state() -> None:
    details = OrderDetails(customer_name="Diego")

    execution = update_order_details(details, {"requested_date": "27-07-2026"})

    assert execution.details is details
    assert execution.result.to_dict()["errors"][0] == {
        "code": "invalid_argument",
        "message": "requested_date must use YYYY-MM-DD format.",
        "field": "requested_date",
    }


def test_validate_and_summarize_order_use_current_domain_rules() -> None:
    cart = cart_with_brownie()
    delivery_details = valid_delivery_details()
    pickup_details = OrderDetails(
        customer_name="Diego Valdettaro",
        customer_phone="999888777",
        fulfillment_type="pickup",
        requested_date=date(2026, 7, 27),
        pickup_store="Benavides",
    )

    validation = validate_order_details_tool(delivery_details, reference_date=REFERENCE_DATE)
    delivery_summary = get_order_summary(cart, delivery_details, reference_date=REFERENCE_DATE)
    pickup_summary = get_order_summary(cart, pickup_details, reference_date=REFERENCE_DATE)

    assert validation.to_dict()["data"]["validation"]["is_valid"] is True
    assert delivery_summary.to_dict()["data"] == {
        "subtotal": "8.00",
        "delivery_fee": "10.00",
        "total": "18.00",
        "validation": {"is_valid": True, "missing_fields": [], "invalid_fields": []},
    }
    assert pickup_summary.to_dict()["data"]["delivery_fee"] == "0.00"
    assert pickup_summary.to_dict()["data"]["total"] == "8.00"


def test_confirm_order_persists_valid_order_and_keeps_id_internal(tmp_path: Path) -> None:
    execution = confirm_order(
        tmp_path / "orders.sqlite3",
        cart_with_brownie(),
        valid_delivery_details(),
        reference_date=REFERENCE_DATE,
    )

    assert execution.order is not None
    assert execution.order.id is not None
    assert execution.order.items[0].product_name == "Brownie de chocolate belga"
    assert execution.result.to_dict() == {
        "ok": True,
        "data": {"confirmed": True, "status": ORDER_STATUS_PENDING},
        "errors": [],
    }


def test_confirm_order_rejects_invalid_order_without_creating_database(tmp_path: Path) -> None:
    database_path = tmp_path / "orders.sqlite3"

    execution = confirm_order(database_path, Cart(), OrderDetails(), reference_date=REFERENCE_DATE)

    assert execution.order is None
    assert execution.result.to_dict()["ok"] is False
    assert {error["code"] for error in execution.result.to_dict()["errors"]} == {
        "empty_cart",
        "missing_required_field",
    }
    assert not database_path.exists()
