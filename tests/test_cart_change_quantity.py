from decimal import Decimal

import pytest

from patty_bot.cart import Cart, CartItem, change_cart_item_quantity
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


def test_change_cart_item_quantity_by_product_id():
    product = make_product()
    cart = Cart(items=(CartItem(product=product, quantity=1),))

    updated_cart = change_cart_item_quantity(cart, "brownie-chocolate-belga", 4)

    assert updated_cart.items == (CartItem(product=product, quantity=4),)
    assert updated_cart.subtotal == Decimal("32.00")


def test_change_cart_item_quantity_preserves_other_items():
    brownie = make_product()
    cheesecake = make_product(
        product_id="cheesecake-oreo",
        name="Cheesecake de Oreo",
        price=Decimal("12.00"),
    )
    cart = Cart(
        items=(
            CartItem(product=brownie, quantity=1),
            CartItem(product=cheesecake, quantity=2),
        )
    )

    updated_cart = change_cart_item_quantity(cart, "brownie-chocolate-belga", 3)

    assert updated_cart.items == (
        CartItem(product=brownie, quantity=3),
        CartItem(product=cheesecake, quantity=2),
    )
    assert updated_cart.subtotal == Decimal("48.00")


def test_change_cart_item_quantity_does_not_mutate_original_cart():
    product = make_product()
    cart = Cart(items=(CartItem(product=product, quantity=1),))

    change_cart_item_quantity(cart, "brownie-chocolate-belga", 4)

    assert cart.items == (CartItem(product=product, quantity=1),)


def test_change_cart_item_quantity_rejects_unknown_product_id():
    product = make_product()
    cart = Cart(items=(CartItem(product=product, quantity=1),))

    with pytest.raises(ValueError, match="Product not found in cart"):
        change_cart_item_quantity(cart, "paneton", 2)


def test_change_cart_item_quantity_rejects_zero_quantity():
    product = make_product()
    cart = Cart(items=(CartItem(product=product, quantity=1),))

    with pytest.raises(ValueError, match="quantity must be greater than zero"):
        change_cart_item_quantity(cart, "brownie-chocolate-belga", 0)


def test_change_cart_item_quantity_rejects_non_integer_quantity():
    product = make_product()
    cart = Cart(items=(CartItem(product=product, quantity=1),))

    with pytest.raises(ValueError, match="quantity must be an integer"):
        change_cart_item_quantity(cart, "brownie-chocolate-belga", 2.5)
