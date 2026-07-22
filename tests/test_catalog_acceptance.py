from pathlib import Path

from patty_bot.catalog import active_products, load_catalog, search_products


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


def test_catalog_acceptance_inactive_products_are_not_offered():
    products = load_catalog(CATALOG_SAMPLE_PATH)
    offered_ids = {product.id for product in active_products(products)}

    assert "cake-naranja" not in offered_ids
    assert product_ids(search_products(products, "Torta de naranja")) == ()


def test_catalog_acceptance_similarity_suggestions_are_limited_to_two():
    products = load_catalog(CATALOG_SAMPLE_PATH)

    result = search_products(products, "red velbet")

    assert len(result.matches) <= 2
    assert set(product_ids(result)) == {"cake-red-velvet-grande", "cake-red-velvet-mediana"}


def test_catalog_acceptance_category_returns_active_category_products():
    products = load_catalog(CATALOG_SAMPLE_PATH)

    result = search_products(products, "Cupcakes")

    assert product_ids(result) == (
        "cupcake-vainilla",
        "cupcake-chocolate",
        "cupcake-red-velvet",
    )


def test_catalog_acceptance_unknown_product_without_similarity_returns_empty():
    products = load_catalog(CATALOG_SAMPLE_PATH)

    result = search_products(products, "paneton")

    assert result.found is False
    assert result.products == ()
