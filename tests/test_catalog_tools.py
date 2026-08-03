"""Tool-boundary tests for structured catalog search results and argument errors."""

from pathlib import Path

from patty_bot.domain.catalog import load_catalog
from patty_bot.tools.catalog_tools import search_catalog


CATALOG_SAMPLE_PATH = Path("data/catalog.sample.csv")


def test_search_catalog_returns_structured_exact_match() -> None:
    products = load_catalog(CATALOG_SAMPLE_PATH)

    result = search_catalog(products, {"query": "brownie"})

    assert result.to_dict() == {
        "ok": True,
        "data": {
            "query": "brownie",
            "found": True,
            "matches": [
                {
                    "product": {
                        "id": "brownie-chocolate-belga",
                        "name": "Brownie de chocolate belga",
                            "category": "Dulcecitos",
                        "price": "8.00",
                    },
                    "match_type": "exact_alias",
                    "score": 1.0,
                }
            ],
        },
        "errors": [],
    }


def test_search_catalog_returns_successful_empty_result_when_no_product_matches() -> None:
    products = load_catalog(CATALOG_SAMPLE_PATH)

    result = search_catalog(products, {"query": "paneton"})

    assert result.to_dict() == {
        "ok": True,
        "data": {"query": "paneton", "found": False, "matches": []},
        "errors": [],
    }


def test_search_catalog_rejects_missing_or_invalid_query() -> None:
    products = load_catalog(CATALOG_SAMPLE_PATH)

    missing_query = search_catalog(products, {})
    non_string_query = search_catalog(products, {"query": 3})

    expected_error = [
        {
            "code": "invalid_argument",
            "message": "query must be a non-empty string.",
            "field": "query",
        }
    ]
    assert missing_query.to_dict() == {"ok": False, "data": {}, "errors": expected_error}
    assert non_string_query.to_dict() == {"ok": False, "data": {}, "errors": expected_error}
