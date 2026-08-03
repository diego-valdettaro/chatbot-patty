"""Acceptance scenarios for catalog availability and search results."""

from pathlib import Path

from patty_bot.domain.catalog import active_products, load_catalog, search_products


CATALOG_SAMPLE_PATH = Path("data/catalog.sample.csv")


def product_ids(result):
    return tuple(product.id for product in result.products)


def test_catalog_acceptance_exact_name():
    products = load_catalog(CATALOG_SAMPLE_PATH)

    result = search_products(products, "Brownie de chocolate belga")

    assert product_ids(result) == ("brownie-chocolate-belga",)


def test_catalog_acceptance_alias():
    products = load_catalog(CATALOG_SAMPLE_PATH)

    result = search_products(products, "box brownies")

    assert product_ids(result) == ("box-brownies-6",)


def test_catalog_acceptance_imported_products_are_all_available():
    products = load_catalog(CATALOG_SAMPLE_PATH)
    offered_ids = {product.id for product in active_products(products)}

    assert len(offered_ids) == 183
    assert product_ids(search_products(products, "paneton")) == ()


def test_catalog_acceptance_similarity_suggestions_are_limited_to_two():
    products = load_catalog(CATALOG_SAMPLE_PATH)

    result = search_products(products, "red velbet")

    assert len(result.matches) <= 2
    assert tuple(product_ids(result)) == ("mini-torta-red-velvet", "cake-red-velvet-grande")


def test_catalog_acceptance_category_returns_active_category_products():
    products = load_catalog(CATALOG_SAMPLE_PATH)

    result = search_products(products, "Individuales")

    assert {"cupcake-chocolate", "cupcake-de-zanahoria"}.issubset(product_ids(result))


def test_catalog_acceptance_unknown_product_without_similarity_returns_empty():
    products = load_catalog(CATALOG_SAMPLE_PATH)

    result = search_products(products, "paneton")

    assert result.found is False
    assert result.products == ()
