from pathlib import Path

from patty_bot.catalog import (
    load_catalog,
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

    result = search_products_by_category(products, "CHEESECAKES")

    assert product_ids(result) == (
        "cheesecake-fresa",
        "cheesecake-maracuya",
        "cheesecake-oreo",
    )


def test_search_similar_products_finds_typo_and_limits_suggestions():
    products = load_catalog(CATALOG_SAMPLE_PATH)

    result = search_similar_products(products, "red velbet")

    assert result.found is True
    assert len(result.matches) <= 2
    assert set(product_ids(result)) == {"cake-red-velvet-grande", "cake-red-velvet-mediana"}
    assert all(match.match_type == "similarity" for match in result.matches)


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
    assert result.matches[0].match_type == "similarity"
