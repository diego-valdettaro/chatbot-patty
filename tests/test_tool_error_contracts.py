"""Cross-tool checks that invalid requests always return controlled JSON errors."""

from datetime import date
from pathlib import Path

from patty_bot.domain.cart import Cart
from patty_bot.tools.cart_tools import add_to_cart, change_cart_quantity
from patty_bot.domain.catalog import load_catalog
from patty_bot.tools.catalog_tools import search_catalog
from patty_bot.tools.order_tools import confirm_order, update_order_details
from patty_bot.domain.orders import OrderDetails


CATALOG_SAMPLE_PATH = Path("data/catalog.sample.csv")
REFERENCE_DATE = date(2026, 7, 26)


def _assert_controlled_error(payload: dict) -> None:
    # Every tool failure must be safe for an agent to inspect without handling Python exceptions.
    assert payload["ok"] is False
    assert payload["data"] == {}
    assert payload["errors"]
    assert all(error["code"] and error["message"] for error in payload["errors"])


def test_invalid_tool_arguments_return_controlled_errors_without_state_changes() -> None:
    products = load_catalog(CATALOG_SAMPLE_PATH)
    cart = Cart()

    catalog_result = search_catalog(products, {"query": ""})
    add_execution = add_to_cart(cart, products, {"product_id": "unknown-product"})
    quantity_execution = change_cart_quantity(cart, {"product_id": "brownie-chocolate-belga", "quantity": True})
    details_execution = update_order_details(OrderDetails(), {"unexpected_field": "value"})

    _assert_controlled_error(catalog_result.to_dict())
    assert add_execution.cart is cart
    _assert_controlled_error(add_execution.result.to_dict())
    assert quantity_execution.cart is cart
    _assert_controlled_error(quantity_execution.result.to_dict())
    assert details_execution.details == OrderDetails()
    _assert_controlled_error(details_execution.result.to_dict())


def test_confirmation_returns_controlled_error_when_sqlite_cannot_open_database(tmp_path: Path) -> None:
    products = load_catalog(CATALOG_SAMPLE_PATH)
    cart = add_to_cart(Cart(), products, {"product_id": "brownie-chocolate-belga"}).cart
    details = OrderDetails(
        customer_name="Diego Valdettaro",
        customer_phone="999888777",
        fulfillment_type="delivery",
        requested_date=date(2026, 7, 28),
        delivery_address="Av. Siempre Viva 123",
    )

    execution = confirm_order(
        tmp_path / "missing-directory" / "orders.sqlite3",
        cart,
        details,
        reference_date=REFERENCE_DATE,
    )

    assert execution.order is None
    payload = execution.result.to_dict()
    _assert_controlled_error(payload)
    assert payload["errors"] == [
        {
            "code": "persistence_failure",
            "message": "The order could not be saved. Please try again.",
        }
    ]
