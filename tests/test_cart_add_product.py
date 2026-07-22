from decimal import Decimal

import pytest

from patty_bot.cart import Cart, CartItem, add_product_to_cart
from patty_bot.catalog import Product


def make_product(
    product_id: str = "brownie-chocolate-belga",
    name: str = "Brownie de chocolate belga",
    price: Decimal = Decimal("8.00"),
    active: bool = True,
) -> Product:
    return Product(
        id=product_id,
        name=name,
        aliases=(),
        category="Brownies",
        price=price,
        active=active,
    )


def test_add_product_to_empty_cart_by_product_id():
    product = make_product()

    cart = add_product_to_cart(Cart(), (product,), "brownie-chocolate-belga")

    assert cart.items == (CartItem(product=product, quantity=1),)
    assert cart.subtotal == Decimal("8.00")


def test_add_product_preserves_existing_items():
    brownie = make_product()
    cheesecake = make_product(
        product_id="cheesecake-oreo",
        name="Cheesecake de Oreo",
        price=Decimal("12.00"),
    )
    cart = Cart(items=(CartItem(product=brownie, quantity=1),))

    updated_cart = add_product_to_cart(cart, (brownie, cheesecake), "cheesecake-oreo")

    assert updated_cart.items == (
        CartItem(product=brownie, quantity=1),
        CartItem(product=cheesecake, quantity=1),
    )
    assert updated_cart.subtotal == Decimal("20.00")


def test_add_existing_product_increments_quantity():
    product = make_product()
    cart = Cart(items=(CartItem(product=product, quantity=1),))

    updated_cart = add_product_to_cart(cart, (product,), "brownie-chocolate-belga")

    assert updated_cart.items == (CartItem(product=product, quantity=2),)
    assert updated_cart.subtotal == Decimal("16.00")


def test_add_product_does_not_mutate_original_cart():
    product = make_product()
    cart = Cart()

    add_product_to_cart(cart, (product,), "brownie-chocolate-belga")

    assert cart.items == ()


def test_add_product_rejects_unknown_product_id():
    product = make_product()

    with pytest.raises(ValueError, match="Active product not found"):
        add_product_to_cart(Cart(), (product,), "paneton")


def test_add_product_rejects_inactive_product():
    product = make_product(active=False)

    with pytest.raises(ValueError, match="Active product not found"):
        add_product_to_cart(Cart(), (product,), "brownie-chocolate-belga")
