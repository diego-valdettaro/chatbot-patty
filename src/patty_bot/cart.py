from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from patty_bot.catalog import Product
from patty_bot.config import DELIVERY_FEE


@dataclass(frozen=True)
class CartItem:
    product: Product
    quantity: int

    def __post_init__(self) -> None:
        if type(self.quantity) is not int:
            raise ValueError("Cart item quantity must be an integer.")
        if self.quantity <= 0:
            raise ValueError("Cart item quantity must be greater than zero.")

    @property
    def line_subtotal(self) -> Decimal:
        return self.product.price * self.quantity


@dataclass(frozen=True)
class Cart:
    items: tuple[CartItem, ...] = ()

    @property
    def is_empty(self) -> bool:
        return len(self.items) == 0

    @property
    def subtotal(self) -> Decimal:
        return sum((item.line_subtotal for item in self.items), Decimal("0"))

    @property
    def delivery_fee(self) -> Decimal:
        return Decimal(str(DELIVERY_FEE))

    @property
    def total(self) -> Decimal:
        return self.subtotal + self.delivery_fee


def add_product_to_cart(cart: Cart, products: Iterable[Product], product_id: str) -> Cart:
    product = _find_active_product_by_id(products, product_id)
    updated_items: list[CartItem] = []
    product_was_in_cart = False

    for item in cart.items:
        if item.product.id == product.id:
            updated_items.append(CartItem(product=item.product, quantity=item.quantity + 1))
            product_was_in_cart = True
        else:
            updated_items.append(item)

    if not product_was_in_cart:
        updated_items.append(CartItem(product=product, quantity=1))

    return Cart(items=tuple(updated_items))


def change_cart_item_quantity(cart: Cart, product_id: str, quantity: int) -> Cart:
    normalized_product_id = product_id.strip()
    updated_items: list[CartItem] = []
    product_was_in_cart = False

    for item in cart.items:
        if item.product.id == normalized_product_id:
            updated_items.append(CartItem(product=item.product, quantity=quantity))
            product_was_in_cart = True
        else:
            updated_items.append(item)

    if not product_was_in_cart:
        raise ValueError(f"Product not found in cart: {product_id}")

    return Cart(items=tuple(updated_items))


def remove_product_from_cart(cart: Cart, product_id: str) -> Cart:
    normalized_product_id = product_id.strip()
    updated_items = tuple(item for item in cart.items if item.product.id != normalized_product_id)

    if len(updated_items) == len(cart.items):
        raise ValueError(f"Product not found in cart: {product_id}")

    return Cart(items=updated_items)


def _find_active_product_by_id(products: Iterable[Product], product_id: str) -> Product:
    normalized_product_id = product_id.strip()
    for product in products:
        if product.id == normalized_product_id and product.active:
            return product

    raise ValueError(f"Active product not found in catalog: {product_id}")
