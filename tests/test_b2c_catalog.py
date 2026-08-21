"""Acceptance tests for the validated B2C catalog used by the application."""

from patty_bot.domain.catalog import load_catalog, search_products
from patty_bot.infrastructure.config import CATALOG_PATH
from patty_bot.tools.catalog_tools import search_catalog
from patty_bot.tools.recommendation_tools import recommend_products


def test_b2c_catalog_loads_only_the_165_standard_active_products() -> None:
    products = load_catalog(CATALOG_PATH)

    assert len(products) == 165
    assert {product.category for product in products}.isdisjoint({"Personalizados"})
    assert all("evento" not in product.description.casefold() for product in products)
    assert all(product.active for product in products)


def test_same_name_variants_are_searchable_and_distinguished_by_presentation() -> None:
    products = load_catalog(CATALOG_PATH)

    variants = search_products(products, "Turron de chocolate")
    large = search_products(products, "Turron de chocolate Grande")

    assert [(match.product.id, match.product.display_name) for match in variants.matches] == [
        ("B2C-001", "Turron de chocolate — Chico"),
        ("B2C-002", "Turron de chocolate — Grande"),
    ]
    assert [(match.product.id, match.product.presentation) for match in large.matches] == [("B2C-002", "Grande")]


def test_b2c_catalog_tool_exposes_merchandising_fields_for_search_and_recommendations() -> None:
    products = load_catalog(CATALOG_PATH)

    search_result = search_catalog(products, {"query": "Turron de chocolate Grande"}).to_dict()
    recommendation_result = recommend_products(
        products,
        {"category": "Tortas", "servings": 12, "max_price": "75.00"},
    ).to_dict()

    product = search_result["data"]["matches"][0]["product"]
    assert product == {
        "id": "B2C-002",
        "name": "Turron de chocolate",
        "category": "Tortas",
        "price": "75.00",
        "presentation": "Grande",
        "display_name": "Turron de chocolate — Grande",
        "portions_or_units": "12 porciones",
        "description": "Turron de chocolate con pecanas, cubierto con fudge casero de Patty.",
    }
    recommendation = next(item for item in recommendation_result["data"]["recommendations"] if item["product_id"] == "B2C-002")
    assert recommendation["presentation"] == "Grande"
    assert recommendation["portions_or_units"] == "12 porciones"
    assert recommendation["description"] == product["description"]
