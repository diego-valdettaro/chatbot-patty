"""Tool-boundary tests for reading and mutating server-side cart state."""

from pathlib import Path

from patty_bot.cart import Cart
from patty_bot.cart_tools import add_to_cart, change_cart_quantity, get_cart, remove_from_cart
from patty_bot.catalog import load_catalog


CATALOG_SAMPLE_PATH = Path("data/catalog.sample.csv")


def test_add_to_cart_returns_updated_server_state_and_serialized_cart() -> None:
    products = load_catalog(CATALOG_SAMPLE_PATH)

    execution = add_to_cart(Cart(), products, {"product_id": "brownie-chocolate-belga"})

    assert execution.cart.items[0].product.id == "brownie-chocolate-belga"
    assert execution.cart.items[0].quantity == 1
    assert execution.result.to_dict() == {
        "ok": True,
        "data": {
            "is_empty": False,
            "item_count": 1,
            "subtotal": "8.00",
            "items": [
                {
                    "product": {
                        "id": "brownie-chocolate-belga",
                        "name": "Brownie de chocolate belga",
                        "category": "Brownies",
                        "price": "8.00",
                    },
                    "quantity": 1,
                    "line_subtotal": "8.00",
                }
            ],
        },
        "errors": [],
    }


def test_add_to_cart_accumulates_existing_product() -> None:
    products = load_catalog(CATALOG_SAMPLE_PATH)
    first_execution = add_to_cart(Cart(), products, {"product_id": "brownie-chocolate-belga"})

    execution = add_to_cart(first_execution.cart, products, {"product_id": "brownie-chocolate-belga"})

    assert execution.cart.items[0].quantity == 2
    assert execution.result.to_dict()["data"]["subtotal"] == "16.00"


def test_change_and_remove_cart_items_return_updated_state() -> None:
    products = load_catalog(CATALOG_SAMPLE_PATH)
    added = add_to_cart(Cart(), products, {"product_id": "brownie-chocolate-belga"})

    changed = change_cart_quantity(added.cart, {"product_id": "brownie-chocolate-belga", "quantity": 3})
    removed = remove_from_cart(changed.cart, {"product_id": "brownie-chocolate-belga"})

    assert changed.result.to_dict()["data"]["item_count"] == 3
    assert changed.result.to_dict()["data"]["subtotal"] == "24.00"
    assert removed.cart == Cart()
    assert removed.result.to_dict()["data"] == {
        "is_empty": True,
        "item_count": 0,
        "subtotal": "0.00",
        "items": [],
    }


def test_get_cart_returns_read_only_snapshot() -> None:
    result = get_cart(Cart())

    assert result.to_dict()["data"] == {
        "is_empty": True,
        "item_count": 0,
        "subtotal": "0.00",
        "items": [],
    }


def test_cart_tools_return_controlled_errors_without_changing_cart() -> None:
    products = load_catalog(CATALOG_SAMPLE_PATH)
    cart = Cart()

    unavailable = add_to_cart(cart, products, {"product_id": "cake-naranja"})
    invalid_quantity = change_cart_quantity(cart, {"product_id": "brownie-chocolate-belga", "quantity": 0})
    missing_item = remove_from_cart(cart, {"product_id": "brownie-chocolate-belga"})

    assert unavailable.cart is cart
    assert unavailable.result.to_dict()["errors"][0]["code"] == "product_not_available"
    assert invalid_quantity.cart is cart
    assert invalid_quantity.result.to_dict()["errors"][0] == {
        "code": "invalid_argument",
        "message": "quantity must be an integer greater than zero.",
        "field": "quantity",
    }
    assert missing_item.cart is cart
    assert missing_item.result.to_dict()["errors"][0]["code"] == "product_not_in_cart"
