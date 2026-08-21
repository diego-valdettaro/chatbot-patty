"""Shared channel-safe serialization for catalog products."""

from patty_bot.agent.tool_contracts import JsonValue
from patty_bot.domain.catalog import Product


def serialize_product(product: Product) -> dict[str, JsonValue]:
    """Expose B2C merchandising details without changing legacy tool payloads."""

    payload: dict[str, JsonValue] = {
        "id": product.id,
        "name": product.name,
        "category": product.category,
        "price": f"{product.price:.2f}",
    }
    if product.presentation:
        payload["presentation"] = product.presentation
        payload["display_name"] = product.display_name
    if product.portions_or_units:
        payload["portions_or_units"] = product.portions_or_units
    if product.description:
        payload["description"] = product.description
    return payload
