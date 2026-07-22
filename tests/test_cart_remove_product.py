from decimal import Decimal

import pytest

from patty_bot.cart import Cart, CartItem, remove_product_from_cart
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


def test_remove_product_from_cart_by_product_id():
    brownie = make_product()
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

    updated_cart = remove_product_from_cart(cart, "brownie-chocolate-belga")

    assert updated_cart.items == (CartItem(product=cheesecake, quantity=1),)
    assert updated_cart.subtotal == Decimal("12.00")


def test_remove_product_can_leave_empty_cart():
    product = make_product()
    cart = Cart(items=(CartItem(product=product, quantity=1),))

    updated_cart = remove_product_from_cart(cart, "brownie-chocolate-belga")

    assert updated_cart.is_empty is True
    assert updated_cart.items == ()


def test_remove_product_does_not_mutate_original_cart():
    product = make_product()
    cart = Cart(items=(CartItem(product=product, quantity=1),))

    remove_product_from_cart(cart, "brownie-chocolate-belga")

    assert cart.items == (CartItem(product=product, quantity=1),)


def test_remove_product_rejects_unknown_product_id():
    product = make_product()
    cart = Cart(items=(CartItem(product=product, quantity=1),))

    with pytest.raises(ValueError, match="Product not found in cart"):
        remove_product_from_cart(cart, "paneton")
