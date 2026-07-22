from decimal import Decimal
from pathlib import Path

import pytest

from patty_bot.cart import (
    Cart,
    add_product_to_cart,
    change_cart_item_quantity,
    remove_product_from_cart,
)
from patty_bot.catalog import load_catalog


CATALOG_SAMPLE_PATH = Path("data/catalog.sample.csv")


def product_quantities(cart: Cart) -> dict[str, int]:
    return {item.product.id: item.quantity for item in cart.items}


def test_cart_acceptance_add_two_products_change_quantity_and_total():
    products = load_catalog(CATALOG_SAMPLE_PATH)

    cart = add_product_to_cart(Cart(), products, "brownie-chocolate-belga")
    cart = add_product_to_cart(cart, products, "cheesecake-oreo")
    cart = change_cart_item_quantity(cart, "brownie-chocolate-belga", 3)

    assert product_quantities(cart) == {
        "brownie-chocolate-belga": 3,
        "cheesecake-oreo": 1,
    }
    assert cart.subtotal == Decimal("104.00")
    assert cart.delivery_fee == Decimal("10")
    assert cart.total == Decimal("114.00")


def test_cart_acceptance_reject_invalid_quantity():
    products = load_catalog(CATALOG_SAMPLE_PATH)
    cart = add_product_to_cart(Cart(), products, "brownie-chocolate-belga")

    with pytest.raises(ValueError, match="quantity must be greater than zero"):
        change_cart_item_quantity(cart, "brownie-chocolate-belga", 0)


def test_cart_acceptance_remove_product_recalculates_subtotal():
    products = load_catalog(CATALOG_SAMPLE_PATH)
    cart = add_product_to_cart(Cart(), products, "brownie-chocolate-belga")
    cart = add_product_to_cart(cart, products, "cheesecake-oreo")

    cart = remove_product_from_cart(cart, "brownie-chocolate-belga")

    assert product_quantities(cart) == {"cheesecake-oreo": 1}
    assert cart.subtotal == Decimal("80.00")
    assert cart.total == Decimal("90.00")


def test_cart_acceptance_rejects_inactive_catalog_product():
    products = load_catalog(CATALOG_SAMPLE_PATH)

    with pytest.raises(ValueError, match="Active product not found"):
        add_product_to_cart(Cart(), products, "cake-naranja")
