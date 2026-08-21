from dataclasses import dataclass
from typing import Iterable, Mapping

from patty_bot.domain.cart import Cart, add_product_to_cart, change_cart_item_quantity, remove_product_from_cart
from patty_bot.domain.catalog import Product
from patty_bot.agent.tool_contracts import JsonValue, ToolError, ToolResult, tool_failure, tool_success
from patty_bot.tools.product_serialization import serialize_product


@dataclass(frozen=True)
class CartToolExecution:
    """A cart tool result plus the server-side cart state after the operation."""

    cart: Cart
    result: ToolResult


def get_cart(cart: Cart) -> ToolResult:
    return tool_success(_serialize_cart(cart))


def add_to_cart(
    cart: Cart,
    products: Iterable[Product],
    arguments: Mapping[str, JsonValue],
) -> CartToolExecution:
    product_id = _product_id_from(arguments)
    if product_id is None:
        return _failed_execution(cart, "product_id must be a non-empty string.", "product_id")

    # Convert domain exceptions into controlled results that an agent can recover from.
    try:
        updated_cart = add_product_to_cart(cart, products, product_id)
    except ValueError:
        return _failed_execution(cart, "The product is not available in the catalog.", "product_id", "product_not_available")

    return CartToolExecution(cart=updated_cart, result=tool_success(_serialize_cart(updated_cart)))


def change_cart_quantity(
    cart: Cart,
    arguments: Mapping[str, JsonValue],
) -> CartToolExecution:
    product_id = _product_id_from(arguments)
    if product_id is None:
        return _failed_execution(cart, "product_id must be a non-empty string.", "product_id")

    # bool is intentionally rejected even though Python treats it as an int.
    quantity = arguments.get("quantity")
    if type(quantity) is not int or quantity <= 0:
        return _failed_execution(cart, "quantity must be an integer greater than zero.", "quantity")

    try:
        updated_cart = change_cart_item_quantity(cart, product_id, quantity)
    except ValueError:
        return _failed_execution(cart, "The product is not in the cart.", "product_id", "product_not_in_cart")

    return CartToolExecution(cart=updated_cart, result=tool_success(_serialize_cart(updated_cart)))


def remove_from_cart(cart: Cart, arguments: Mapping[str, JsonValue]) -> CartToolExecution:
    product_id = _product_id_from(arguments)
    if product_id is None:
        return _failed_execution(cart, "product_id must be a non-empty string.", "product_id")

    try:
        updated_cart = remove_product_from_cart(cart, product_id)
    except ValueError:
        return _failed_execution(cart, "The product is not in the cart.", "product_id", "product_not_in_cart")

    return CartToolExecution(cart=updated_cart, result=tool_success(_serialize_cart(updated_cart)))


def _product_id_from(arguments: Mapping[str, JsonValue]) -> str | None:
    product_id = arguments.get("product_id")
    return product_id.strip() if isinstance(product_id, str) and product_id.strip() else None


def _failed_execution(
    cart: Cart,
    message: str,
    field: str,
    code: str = "invalid_argument",
) -> CartToolExecution:
    return CartToolExecution(
        cart=cart,
        result=tool_failure(ToolError(code=code, message=message, field=field)),
    )


def _serialize_cart(cart: Cart) -> dict[str, JsonValue]:
    # Delivery and total are intentionally omitted because fulfillment mode belongs to order details.
    return {
        "is_empty": cart.is_empty,
        "item_count": sum(item.quantity for item in cart.items),
        "subtotal": f"{cart.subtotal:.2f}",
        "items": [
            {
                "product": serialize_product(item.product),
                "quantity": item.quantity,
                "line_subtotal": f"{item.line_subtotal:.2f}",
            }
            for item in cart.items
        ],
    }
