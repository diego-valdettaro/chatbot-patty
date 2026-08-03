"""Unit tests for catalog exact, category, and fuzzy search priority."""

from decimal import Decimal
from pathlib import Path

from patty_bot.domain.catalog import (
    load_catalog,
    Product,
    search_products,
    search_products_by_category,
    search_similar_products,
)


CATALOG_SAMPLE_PATH = Path("data/catalog.sample.csv")


def product_ids(result):
    return tuple(product.id for product in result.products)


def test_search_products_by_category_returns_active_products():
    products = load_catalog(CATALOG_SAMPLE_PATH)

    result = search_products_by_category(products, "tortas")

    assert result.found is True
    assert "cake-red-velvet-mediana" in product_ids(result)
    assert "cake-red-velvet-grande" in product_ids(result)
    assert "cake-naranja" not in product_ids(result)
    assert all(match.match_type == "category" for match in result.matches)


def test_search_products_by_category_ignores_accents_and_case():
    products = load_catalog(CATALOG_SAMPLE_PATH)

    result = search_products_by_category(products, "INDIVIDUALES")

    assert "cheesecake-oreo" in product_ids(result)


def test_search_similar_products_finds_typo_and_limits_suggestions():
    products = load_catalog(CATALOG_SAMPLE_PATH)

    result = search_similar_products(products, "red velbet")

    assert result.found is True
    assert len(result.matches) <= 2
    assert product_ids(result) == ("mini-torta-red-velvet", "cake-red-velvet-grande")
    assert all(match.match_type == "fuzzy_name" for match in result.matches)


def test_search_similar_products_returns_empty_when_similarity_is_low():
    products = load_catalog(CATALOG_SAMPLE_PATH)

    result = search_similar_products(products, "paneton")

    assert result.found is False
    assert result.products == ()


def test_search_products_prefers_exact_match_before_similarity():
    products = load_catalog(CATALOG_SAMPLE_PATH)

    result = search_products(products, "brownie")

    assert result.found is True
    assert product_ids(result) == ("brownie-chocolate-belga",)
    assert result.matches[0].match_type == "exact_alias"


def test_search_products_falls_back_to_category():
    products = load_catalog(CATALOG_SAMPLE_PATH)

    result = search_products(products, "brownies")

    assert result.found is True
    assert result.matches[0].match_type == "exact_alias"


def test_search_products_falls_back_to_similarity():
    products = load_catalog(CATALOG_SAMPLE_PATH)

    result = search_products(products, "chesecake oreo")

    assert product_ids(result)[0] == "cheesecake-oreo"
    assert len(result.matches) <= 2
    assert result.matches[0].match_type == "fuzzy_name"


def test_search_products_returns_all_ambiguous_partial_name_matches() -> None:
    products = load_catalog(CATALOG_SAMPLE_PATH)

    result = search_products(products, "bombita")

    assert len(result.matches) == 14
    assert "bombita-de-chocolucuma" in product_ids(result)
    assert all(match.match_type == "partial_name" for match in result.matches)


def test_search_products_normalizes_accents_for_partial_name_matches() -> None:
    products = (
        Product(
            id="bombita-chocolucuma",
            name="Bombita de chocolúcuma",
            aliases=(),
            category="Individuales",
            price=Decimal("22.00"),
            active=True,
        ),
    )

    result = search_products(products, "chocolucuma")

    assert product_ids(result) == ("bombita-chocolucuma",)
    assert result.matches[0].match_type == "partial_name"


def test_search_products_ranks_specific_partial_name_above_fuzzy_matches() -> None:
    products = load_catalog(CATALOG_SAMPLE_PATH)

    result = search_products(products, "bombita chocolucuma")

    assert result.matches[0].product.id == "bombita-de-chocolucuma"
    assert result.matches[0].match_type == "partial_name"


def test_search_products_finds_prefixes_and_typos_with_rapidfuzz() -> None:
    products = load_catalog(CATALOG_SAMPLE_PATH)

    prefix_result = search_products(products, "chocolu")
    typo_result = search_products(products, "chocolukuma")

    assert prefix_result.matches[0].product.id == "bombita-de-chocolucuma"
    assert prefix_result.matches[0].match_type == "partial_name"
    assert typo_result.matches[0].product.id == "bombita-de-chocolucuma"
    assert typo_result.matches[0].match_type == "fuzzy_name"


def test_search_products_considers_aliases_and_ranks_names_above_categories() -> None:
    products = (
        Product(
            id="alias",
            name="Producto especial",
            aliases=("dulce bombita",),
            category="Dulcecitos",
            price=Decimal("10.00"),
            active=True,
        ),
        Product(
            id="name",
            name="Torta de chocolate",
            aliases=(),
            category="Dulcecitos",
            price=Decimal("10.00"),
            active=True,
        ),
        Product(
            id="category",
            name="Producto de la casa",
            aliases=(),
            category="Torta",
            price=Decimal("10.00"),
            active=True,
        ),
    )

    alias_result = search_products(products, "bombita")
    category_result = search_products(products, "torta")

    assert product_ids(alias_result) == ("alias",)
    assert alias_result.matches[0].match_type == "partial_alias"
    assert product_ids(category_result) == ("name", "category")
    assert tuple(match.match_type for match in category_result.matches) == ("partial_name", "category")


def test_search_products_orders_equal_scores_deterministically_and_ignores_short_noise() -> None:
    products = (
        Product("z", "Bombita zeta", (), "Individuales", Decimal("10.00"), True),
        Product("a", "Bombita alfa", (), "Individuales", Decimal("10.00"), True),
    )

    assert product_ids(search_products(products, "bombita")) == ("a", "z")
    assert search_products(products, "bo").products == ()
