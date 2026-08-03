"""Tests for the agent-facing recommendation tool adapter."""

from decimal import Decimal

import pytest

from patty_bot.domain.catalog import Product
from patty_bot.tools.recommendation_tools import recommend_products


def products() -> tuple[Product, ...]:
    return (
        Product(
            id="cake",
            name="Torta de chocolate",
            aliases=(),
            category="Tortas",
            price=Decimal("95.00"),
            active=True,
            servings_min=8,
            servings_max=12,
            allergens=("gluten",),
        ),
        Product(
            id="inactive",
            name="Torta inactiva",
            aliases=(),
            category="Tortas",
            price=Decimal("80.00"),
            active=False,
        ),
    )


def test_recommend_products_builds_request_and_serializes_domain_result() -> None:
    result = recommend_products(
        products(),
        {
            "category": "Tortas",
            "servings": 10,
            "excluded_allergens": [],
            "max_price": "100.00",
        },
    )

    assert result.to_dict() == {
        "ok": True,
        "data": {
            "recommendations": [
                {
                    "product_id": "cake",
                    "name": "Torta de chocolate",
                    "category": "Tortas",
                    "price": "95.00",
                    "score": 100,
                    "reasons": ["category_match", "servings_match", "within_budget"],
                }
            ]
        },
        "errors": [],
    }


def test_recommend_products_returns_a_successful_empty_result() -> None:
    result = recommend_products(products(), {"max_price": "50.00"})

    assert result.to_dict() == {"ok": True, "data": {"recommendations": []}, "errors": []}


@pytest.mark.parametrize(
    ("arguments", "field"),
    (
        ({"servings": -1}, "servings"),
        ({"servings": True}, "servings"),
        ({"max_price": "not-a-decimal"}, "max_price"),
        ({"max_price": "-1.00"}, "max_price"),
        ({"excluded_allergens": [""]}, "excluded_allergens"),
        ({"excluded_allergens": "gluten"}, "excluded_allergens"),
        ({"category": 3}, "category"),
    ),
)
def test_recommend_products_returns_controlled_errors_for_invalid_arguments(arguments: dict, field: str) -> None:
    result = recommend_products(products(), arguments)

    assert result.ok is False
    assert result.to_dict()["errors"][0]["code"] == "invalid_argument"
    assert result.to_dict()["errors"][0]["field"] == field
