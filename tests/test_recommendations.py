"""Tests for deterministic, catalog-only product recommendations."""

from decimal import Decimal

import pytest

from patty_bot.domain.catalog import Product
from patty_bot.domain.recommendations import (
    CATEGORY_MATCH_SCORE,
    SERVINGS_MATCH_SCORE,
    WITHIN_BUDGET_SCORE,
    RecommendationRequest,
    RecommendationService,
)


def product(
    product_id: str,
    *,
    name: str | None = None,
    category: str = "Tortas",
    price: str = "50.00",
    active: bool = True,
    servings_min: int | None = 8,
    servings_max: int | None = 12,
    allergens: tuple[str, ...] = (),
) -> Product:
    return Product(
        id=product_id,
        name=name or product_id,
        aliases=(),
        category=category,
        price=Decimal(price),
        active=active,
        servings_min=servings_min,
        servings_max=servings_max,
        allergens=allergens,
    )


def ids(result) -> tuple[str, ...]:
    return tuple(recommendation.product.id for recommendation in result.recommendations)


def test_excludes_inactive_products() -> None:
    service = RecommendationService((product("active"), product("inactive", active=False)))

    assert ids(service.recommend(RecommendationRequest())) == ("active",)


def test_excludes_products_with_normalized_incompatible_allergens() -> None:
    service = RecommendationService((
        product("with-nuts", allergens=(" Frutos Secos ",)),
        product("safe", allergens=("lacteos",)),
    ))

    result = service.recommend(RecommendationRequest(excluded_allergens=("frutos   secos",)))

    assert ids(result) == ("safe",)


def test_category_match_adds_score_and_reason_without_excluding_other_categories() -> None:
    service = RecommendationService((product("cake"), product("cookie", category="Dulcecitos")))

    result = service.recommend(RecommendationRequest(category="  TORTAS  "))

    assert ids(result) == ("cake", "cookie")
    assert result.recommendations[0].score == CATEGORY_MATCH_SCORE
    assert result.recommendations[0].reasons == ("category_match",)
    assert result.recommendations[1].score == 0


def test_servings_match_adds_score_and_reason() -> None:
    service = RecommendationService((product("large", servings_min=8, servings_max=12), product("small", servings_min=1, servings_max=4)))

    result = service.recommend(RecommendationRequest(servings=10))

    assert ids(result) == ("large", "small")
    assert result.recommendations[0].score == SERVINGS_MATCH_SCORE
    assert result.recommendations[0].reasons == ("servings_match",)


def test_products_without_servings_data_remain_without_a_servings_reason() -> None:
    service = RecommendationService((product("known", servings_min=8, servings_max=12), product("unknown", servings_min=None, servings_max=None)))

    result = service.recommend(RecommendationRequest(servings=10))

    assert ids(result) == ("known", "unknown")
    assert result.recommendations[1].score == 0
    assert result.recommendations[1].reasons == ()


def test_budget_is_a_hard_constraint_and_scores_compatible_products() -> None:
    service = RecommendationService((product("within", price="50.00"), product("over", price="50.01")))

    result = service.recommend(RecommendationRequest(max_price=Decimal("50.00")))

    assert ids(result) == ("within",)
    assert result.recommendations[0].score == WITHIN_BUDGET_SCORE
    assert result.recommendations[0].reasons == ("within_budget",)


def test_ranking_combines_centralized_scores() -> None:
    service = RecommendationService((
        product("all-matches", price="50.00", category="Tortas", servings_min=8, servings_max=12),
        product("category-only", price="100.00", category="Tortas", servings_min=1, servings_max=2),
    ))

    result = service.recommend(RecommendationRequest(category="Tortas", servings=10, max_price=Decimal("100.00")))

    assert ids(result) == ("all-matches", "category-only")
    assert result.recommendations[0].score == CATEGORY_MATCH_SCORE + SERVINGS_MATCH_SCORE + WITHIN_BUDGET_SCORE
    assert result.recommendations[0].reasons == ("category_match", "servings_match", "within_budget")


def test_equal_scores_are_ordered_stably_by_name_then_id() -> None:
    service = RecommendationService((product("z-id", name="Zeta"), product("a-id", name="Alfa"), product("a-second", name="Alfa")))

    assert ids(service.recommend(RecommendationRequest())) == ("a-id", "a-second", "z-id")


@pytest.mark.parametrize(
    "request_kwargs",
    (
        {"servings": -1},
        {"max_price": Decimal("-0.01")},
        {"excluded_allergens": (" ",)},
        {"excluded_allergens": (1,)},
    ),
)
def test_request_rejects_invalid_inputs(request_kwargs: dict) -> None:
    with pytest.raises(ValueError):
        RecommendationRequest(**request_kwargs)


def test_same_inputs_always_produce_the_same_recommendations() -> None:
    service = RecommendationService((product("b", name="Beta"), product("a", name="Alfa")))
    request = RecommendationRequest(category="Tortas", servings=10, max_price=Decimal("50.00"))

    assert service.recommend(request) == service.recommend(request)
