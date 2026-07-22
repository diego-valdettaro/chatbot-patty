from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

from patty_bot.catalog import active_products, load_catalog


CATALOG_SAMPLE_PATH = Path("data/catalog.sample.csv")
TEST_TMP_DIR = Path("tests/.tmp")


def write_catalog(content: str) -> Path:
    TEST_TMP_DIR.mkdir(exist_ok=True)
    catalog_path = TEST_TMP_DIR / f"catalog-{uuid4().hex}.csv"
    catalog_path.write_text(content, encoding="utf-8")
    return catalog_path


def test_load_catalog_sample_file():
    products = load_catalog(CATALOG_SAMPLE_PATH)

    assert len(products) == 30


def test_load_catalog_sample_active_products():
    products = load_catalog(CATALOG_SAMPLE_PATH)

    assert len(active_products(products)) == 29
    assert sum(1 for product in products if not product.active) == 1


def test_load_catalog_parses_aliases_and_decimal_price():
    products = load_catalog(CATALOG_SAMPLE_PATH)
    brownie = next(product for product in products if product.id == "brownie-chocolate-belga")

    assert brownie.aliases == ("brownie", "brownies", "brownie chocolate")
    assert brownie.price == Decimal("8.00")


def test_load_catalog_rejects_missing_required_column():
    catalog_path = write_catalog(
        "id,name,aliases,category,price\n"
        "brownie,Brownie,brownie,Brownies,8.00\n",
    )

    with pytest.raises(ValueError, match="missing required columns: active"):
        load_catalog(catalog_path)


def test_load_catalog_rejects_invalid_price():
    catalog_path = write_catalog(
        "id,name,aliases,category,price,active\n"
        "brownie,Brownie,brownie,Brownies,ocho,true\n",
    )

    with pytest.raises(ValueError, match="price must be a valid decimal"):
        load_catalog(catalog_path)


def test_load_catalog_rejects_invalid_active_value():
    catalog_path = write_catalog(
        "id,name,aliases,category,price,active\n"
        "brownie,Brownie,brownie,Brownies,8.00,yes\n",
    )

    with pytest.raises(ValueError, match="active must be true or false"):
        load_catalog(catalog_path)


def test_load_catalog_rejects_duplicate_ids():
    catalog_path = write_catalog(
        "id,name,aliases,category,price,active\n"
        "brownie,Brownie,brownie,Brownies,8.00,true\n"
        "brownie,Brownie grande,brownie grande,Brownies,10.00,true\n",
    )

    with pytest.raises(ValueError, match="duplicate product ids: brownie"):
        load_catalog(catalog_path)
