import csv
from difflib import SequenceMatcher
import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable


REQUIRED_CATALOG_COLUMNS = ("id", "name", "aliases", "category", "price", "active")
SIMILARITY_THRESHOLD = 0.72


@dataclass(frozen=True)
class Product:
    id: str
    name: str
    aliases: tuple[str, ...]
    category: str
    price: Decimal
    active: bool

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("Product id cannot be empty.")
        if not self.name.strip():
            raise ValueError("Product name cannot be empty.")
        if not self.category.strip():
            raise ValueError("Product category cannot be empty.")
        if self.price < Decimal("0"):
            raise ValueError("Product price cannot be negative.")


@dataclass(frozen=True)
class CatalogMatch:
    product: Product
    match_type: str
    score: float

    def __post_init__(self) -> None:
        if not self.match_type.strip():
            raise ValueError("Match type cannot be empty.")
        if self.score < 0:
            raise ValueError("Match score cannot be negative.")


@dataclass(frozen=True)
class CatalogSearchResult:
    query: str
    matches: tuple[CatalogMatch, ...]

    @property
    def found(self) -> bool:
        return len(self.matches) > 0

    @property
    def products(self) -> tuple[Product, ...]:
        return tuple(match.product for match in self.matches)


def load_catalog(path: str | Path) -> tuple[Product, ...]:
    with Path(path).open(newline="", encoding="utf-8") as catalog_file:
        reader = csv.DictReader(catalog_file)
        _validate_required_columns(reader.fieldnames)
        products = tuple(_product_from_row(row, row_number) for row_number, row in enumerate(reader, start=2))

    _validate_unique_ids(products)
    return products


def active_products(products: Iterable[Product]) -> tuple[Product, ...]:
    return tuple(product for product in products if product.active)


def search_exact_products(products: Iterable[Product], query: str) -> CatalogSearchResult:
    normalized_query = _normalize_text(query)
    if not normalized_query:
        return CatalogSearchResult(query=query, matches=())

    matches: list[CatalogMatch] = []
    for product in active_products(products):
        normalized_name = _normalize_text(product.name)
        if normalized_name == normalized_query:
            matches.append(CatalogMatch(product=product, match_type="exact_name", score=1.0))
            continue

        normalized_aliases = {_normalize_text(alias) for alias in product.aliases}
        if normalized_query in normalized_aliases:
            matches.append(CatalogMatch(product=product, match_type="exact_alias", score=1.0))

    return CatalogSearchResult(query=query, matches=tuple(matches))


def search_products(
    products: Iterable[Product],
    query: str,
    max_similarity_matches: int = 2,
) -> CatalogSearchResult:
    exact_result = search_exact_products(products, query)
    if exact_result.found:
        return exact_result

    category_result = search_products_by_category(products, query)
    if category_result.found:
        return category_result

    return search_similar_products(products, query, max_matches=max_similarity_matches)


def search_products_by_category(products: Iterable[Product], query: str) -> CatalogSearchResult:
    normalized_query = _normalize_text(query)
    if not normalized_query:
        return CatalogSearchResult(query=query, matches=())

    matches = tuple(
        CatalogMatch(product=product, match_type="category", score=1.0)
        for product in active_products(products)
        if _normalize_text(product.category) == normalized_query
    )
    return CatalogSearchResult(query=query, matches=matches)


def search_similar_products(
    products: Iterable[Product],
    query: str,
    max_matches: int = 2,
) -> CatalogSearchResult:
    normalized_query = _normalize_text(query)
    if not normalized_query or max_matches <= 0:
        return CatalogSearchResult(query=query, matches=())

    scored_matches: list[CatalogMatch] = []
    for product in active_products(products):
        score = max(_similarity_score(normalized_query, candidate) for candidate in _search_candidates(product))
        if score >= SIMILARITY_THRESHOLD:
            scored_matches.append(CatalogMatch(product=product, match_type="similarity", score=score))

    ordered_matches = sorted(scored_matches, key=lambda match: (-match.score, match.product.name))
    return CatalogSearchResult(query=query, matches=tuple(ordered_matches[:max_matches]))


def _validate_required_columns(fieldnames: list[str] | None) -> None:
    if fieldnames is None:
        raise ValueError("Catalog CSV is empty.")

    missing_columns = [column for column in REQUIRED_CATALOG_COLUMNS if column not in fieldnames]
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise ValueError(f"Catalog CSV is missing required columns: {missing}.")


def _product_from_row(row: dict[str, str], row_number: int) -> Product:
    try:
        return Product(
            id=row["id"].strip(),
            name=row["name"].strip(),
            aliases=_parse_aliases(row["aliases"]),
            category=row["category"].strip(),
            price=_parse_price(row["price"], row_number),
            active=_parse_active(row["active"], row_number),
        )
    except ValueError as error:
        raise ValueError(f"Invalid catalog row {row_number}: {error}") from error


def _parse_aliases(value: str) -> tuple[str, ...]:
    return tuple(alias.strip() for alias in value.split("|") if alias.strip())


def _parse_price(value: str, row_number: int) -> Decimal:
    try:
        return Decimal(value.strip())
    except InvalidOperation as error:
        raise ValueError(f"price must be a valid decimal in row {row_number}") from error


def _parse_active(value: str, row_number: int) -> bool:
    normalized = value.strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False

    raise ValueError(f"active must be true or false in row {row_number}")


def _validate_unique_ids(products: tuple[Product, ...]) -> None:
    seen_ids: set[str] = set()
    duplicate_ids: set[str] = set()

    for product in products:
        if product.id in seen_ids:
            duplicate_ids.add(product.id)
        seen_ids.add(product.id)

    if duplicate_ids:
        duplicates = ", ".join(sorted(duplicate_ids))
        raise ValueError(f"Catalog CSV contains duplicate product ids: {duplicates}.")


def _normalize_text(value: str) -> str:
    without_accents = "".join(
        character
        for character in unicodedata.normalize("NFD", value)
        if unicodedata.category(character) != "Mn"
    )
    normalized_spaces = re.sub(r"\s+", " ", without_accents)
    return normalized_spaces.strip().lower()


def _search_candidates(product: Product) -> tuple[str, ...]:
    return tuple(_normalize_text(candidate) for candidate in (product.name, *product.aliases))


def _similarity_score(query: str, candidate: str) -> float:
    return SequenceMatcher(None, query, candidate).ratio()
