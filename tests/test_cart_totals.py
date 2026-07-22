from decimal import Decimal

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


def test_empty_cart_total_includes_delivery_fee():
    cart = Cart()

    assert cart.subtotal == Decimal("0")
    assert cart.delivery_fee == Decimal("10")
    assert cart.total == Decimal("10")


def test_cart_total_uses_catalog_prices_and_delivery_fee():
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

    assert cart.subtotal == Decimal("28.00")
    assert cart.delivery_fee == Decimal("10")
    assert cart.total == Decimal("38.00")
