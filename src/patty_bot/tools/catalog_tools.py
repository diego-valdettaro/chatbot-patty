from typing import Iterable, Mapping

from patty_bot.domain.catalog import CatalogMatch, Product, search_products
from patty_bot.agent.tool_contracts import JsonValue, ToolError, ToolResult, tool_failure, tool_success
from patty_bot.tools.product_serialization import serialize_product


def search_catalog(
    products: Iterable[Product],
    arguments: Mapping[str, JsonValue],
) -> ToolResult:
    """Search active catalog products using a structured tool request."""

    query = arguments.get("query")
    # Tool inputs are validated here; catalog search itself remains focused on search behavior.
    if not isinstance(query, str) or not query.strip():
        return tool_failure(
            ToolError(
                code="invalid_argument",
                message="query must be a non-empty string.",
                field="query",
            )
        )

    # Reuse the domain's exact/category/fuzzy priority rather than creating agent-specific rules.
    result = search_products(products, query)
    return tool_success(
        {
            "query": result.query,
            "found": result.found,
            "matches": [_serialize_match(match) for match in result.matches],
        }
    )


def _serialize_match(match: CatalogMatch) -> dict[str, JsonValue]:
    # Decimal prices cross the tool boundary as strings to preserve exact currency values.
    product = match.product
    return {
        "product": serialize_product(product),
        "match_type": match.match_type,
        "score": match.score,
    }
