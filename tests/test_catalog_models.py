from decimal import Decimal

import pytest

from patty_bot.catalog import CatalogMatch, CatalogSearchResult, Product


def make_product() -> Product:
    return Product(
        id="brownie-chocolate-belga",
        name="Brownie de chocolate belga",
        aliases=("brownie", "brownies"),
        category="Brownies",
        price=Decimal("8.00"),
        active=True,
    )


def test_product_keeps_catalog_fields():
    product = make_product()

    assert product.id == "brownie-chocolate-belga"
    assert product.name == "Brownie de chocolate belga"
    assert product.aliases == ("brownie", "brownies")
    assert product.category == "Brownies"
    assert product.price == Decimal("8.00")
    assert product.active is True


def test_product_rejects_empty_required_fields():
    with pytest.raises(ValueError, match="Product id cannot be empty"):
        Product(
            id=" ",
            name="Brownie",
            aliases=(),
            category="Brownies",
            price=Decimal("8.00"),
            active=True,
        )


def test_product_rejects_negative_price():
    with pytest.raises(ValueError, match="Product price cannot be negative"):
        Product(
            id="brownie",
            name="Brownie",
            aliases=(),
            category="Brownies",
            price=Decimal("-1.00"),
            active=True,
        )


def test_search_result_reports_found_products():
    product = make_product()
    match = CatalogMatch(product=product, match_type="exact", score=1.0)
    result = CatalogSearchResult(query="brownie", matches=(match,))

    assert result.found is True
    assert result.products == (product,)


def test_search_result_reports_empty_result():
    result = CatalogSearchResult(query="paneton", matches=())

    assert result.found is False
    assert result.products == ()
