from pathlib import Path

from patty_bot.catalog import load_catalog, search_exact_products


CATALOG_SAMPLE_PATH = Path("data/catalog.sample.csv")


def product_ids(result):
    return tuple(product.id for product in result.products)


def test_search_exact_products_finds_by_exact_name():
    products = load_catalog(CATALOG_SAMPLE_PATH)

    result = search_exact_products(products, "Brownie de chocolate belga")

    assert result.found is True
    assert product_ids(result) == ("brownie-chocolate-belga",)
    assert result.matches[0].match_type == "exact_name"


def test_search_exact_products_finds_by_alias():
    products = load_catalog(CATALOG_SAMPLE_PATH)

    result = search_exact_products(products, "brownies x6")

    assert result.found is True
    assert product_ids(result) == ("box-brownies-6",)
    assert result.matches[0].match_type == "exact_alias"


def test_search_exact_products_ignores_case_and_extra_spaces():
    products = load_catalog(CATALOG_SAMPLE_PATH)

    result = search_exact_products(products, "  BROWNIE   CHOCOLATE  ")

    assert product_ids(result) == ("brownie-chocolate-belga",)


def test_search_exact_products_ignores_accents():
    products = load_catalog(CATALOG_SAMPLE_PATH)

    result = search_exact_products(products, "cheesecake de maracuyá")

    assert product_ids(result) == ("cheesecake-maracuya",)


def test_search_exact_products_does_not_return_inactive_products():
    products = load_catalog(CATALOG_SAMPLE_PATH)

    result = search_exact_products(products, "Torta de naranja")

    assert result.found is False
    assert result.products == ()


def test_search_exact_products_returns_empty_for_non_exact_match():
    products = load_catalog(CATALOG_SAMPLE_PATH)

    result = search_exact_products(products, "paneton")

    assert result.found is False
    assert result.products == ()
