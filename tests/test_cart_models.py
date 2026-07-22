from decimal import Decimal

import pytest

from patty_bot.cart import Cart, CartItem
from patty_bot.catalog import Product


def make_product(
    product_id: str = "brownie-chocolate-belga",
    name: str = "Brownie de chocolate belga",
    price: Decimal = Decimal("8.00"),
) -> Product:
    return Product(
        id=product_id,
        name=name,
        aliases=(),
        category="Brownies",
        price=price,
        active=True,
    )


def test_cart_item_keeps_product_and_quantity():
    product = make_product()

    item = CartItem(product=product, quantity=2)

    assert item.product == product
    assert item.quantity == 2


def test_cart_item_rejects_non_integer_quantity():
    product = make_product()

    with pytest.raises(ValueError, match="quantity must be an integer"):
        CartItem(product=product, quantity=1.5)


def test_cart_item_rejects_zero_quantity():
    product = make_product()

    with pytest.raises(ValueError, match="quantity must be greater than zero"):
        CartItem(product=product, quantity=0)


def test_cart_item_rejects_negative_quantity():
    product = make_product()

    with pytest.raises(ValueError, match="quantity must be greater than zero"):
        CartItem(product=product, quantity=-1)


def test_cart_item_calculates_line_subtotal_from_catalog_price():
    product = make_product(price=Decimal("8.50"))

    item = CartItem(product=product, quantity=3)

    assert item.line_subtotal == Decimal("25.50")


def test_empty_cart_has_no_items_and_zero_subtotal():
    cart = Cart()

    assert cart.is_empty is True
    assert cart.items == ()
    assert cart.subtotal == Decimal("0")


def test_cart_calculates_subtotal_from_items():
    brownie = make_product(price=Decimal("8.00"))
    cheesecake = make_product(
        product_id="cheesecake-oreo",
        name="Cheesecake de Oreo",
        price=Decimal("12.00"),
    )

    cart = Cart(
        items=(
            CartItem(product=brownie, quantity=2),
            CartItem(product=cheesecake, quantity=1),
        )
    )

    assert cart.is_empty is False
    assert cart.subtotal == Decimal("28.00")
