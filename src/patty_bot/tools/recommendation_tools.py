"""Tool adapter for structured, deterministic catalog recommendations."""

from collections.abc import Iterable, Mapping
from decimal import Decimal, InvalidOperation

from patty_bot.agent.tool_contracts import JsonValue, ToolError, ToolResult, tool_failure, tool_success
from patty_bot.domain.catalog import Product
from patty_bot.domain.recommendations import RecommendationRequest, RecommendationService
from patty_bot.tools.product_serialization import serialize_product


def recommend_products(
    products: Iterable[Product],
    arguments: Mapping[str, JsonValue],
) -> ToolResult:
    """Validate agent arguments and serialize the domain recommendation result."""

    request_or_error = _build_request(arguments)
    if isinstance(request_or_error, ToolError):
        return tool_failure(request_or_error)

    result = RecommendationService(products).recommend(request_or_error)
    return tool_success(
        {
            "recommendations": [
                {
                    "product_id": recommendation.product.id,
                    **{
                        key: value
                        for key, value in serialize_product(recommendation.product).items()
                        if key != "id"
                    },
                    "score": recommendation.score,
                    "reasons": list(recommendation.reasons),
                }
                for recommendation in result.recommendations
            ]
        }
    )


def _build_request(arguments: Mapping[str, JsonValue]) -> RecommendationRequest | ToolError:
    category = arguments.get("category")
    if category is not None and (not isinstance(category, str) or not category.strip()):
        return _invalid_argument("category", "category must be a non-empty string or null.")

    servings = arguments.get("servings")
    if servings is not None and (isinstance(servings, bool) or not isinstance(servings, int)):
        return _invalid_argument("servings", "servings must be an integer or null.")

    excluded_allergens = arguments.get("excluded_allergens", [])
    if excluded_allergens is None:
        excluded_allergens = []
    if not isinstance(excluded_allergens, list):
        return _invalid_argument("excluded_allergens", "excluded_allergens must be an array of strings.")

    max_price_or_error = _parse_max_price(arguments.get("max_price"))
    if isinstance(max_price_or_error, ToolError):
        return max_price_or_error

    try:
        return RecommendationRequest(
            category=category,
            servings=servings,
            excluded_allergens=tuple(excluded_allergens),
            max_price=max_price_or_error,
        )
    except ValueError as error:
        message = str(error)
        if "excluded_allergens" in message:
            field = "excluded_allergens"
        elif "max_price" in message:
            field = "max_price"
        else:
            field = "servings"
        return _invalid_argument(field, message)


def _parse_max_price(value: JsonValue | None) -> Decimal | ToolError | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        return _invalid_argument("max_price", "max_price must be a decimal string or null.")
    try:
        price = Decimal(value)
    except InvalidOperation:
        return _invalid_argument("max_price", "max_price must be a valid decimal string or null.")
    if not price.is_finite():
        return _invalid_argument("max_price", "max_price must be a valid decimal string or null.")
    return price


def _invalid_argument(field: str, message: str) -> ToolError:
    return ToolError(code="invalid_argument", message=message, field=field)
