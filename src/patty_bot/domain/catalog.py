import csv
import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable

from rapidfuzz import fuzz


# Loading fails early when this minimal product contract is not present in the CSV.
REQUIRED_CATALOG_COLUMNS = (
    "id",
    "name",
    "aliases",
    "category",
    "price",
    "active",
    "servings_min",
    "servings_max",
    "allergens",
)
# RapidFuzz scores are percentages; they are kept here with match priorities so tuning stays explicit.
EXACT_MATCH_SCORE = 1.0
CATEGORY_MATCH_SCORE = 1.0
PARTIAL_MATCH_THRESHOLD = 90.0
FUZZY_MATCH_THRESHOLD = 80.0
MIN_PARTIAL_QUERY_LENGTH = 4
MIN_FUZZY_QUERY_LENGTH = 3
MATCH_TYPE_PRIORITIES = {
    "exact_name": 0,
    "exact_alias": 1,
    "partial_name": 2,
    "partial_alias": 3,
    "fuzzy_name": 4,
    "fuzzy_alias": 5,
    "category": 6,
}


@dataclass(frozen=True)
class Product:
    id: str
    name: str
    aliases: tuple[str, ...]
    category: str
    price: Decimal
    active: bool
    servings_min: int | None = None
    servings_max: int | None = None
    allergens: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("Product id cannot be empty.")
        if not self.name.strip():
            raise ValueError("Product name cannot be empty.")
        if not self.category.strip():
            raise ValueError("Product category cannot be empty.")
        if self.price < Decimal("0"):
            raise ValueError("Product price cannot be negative.")
        if self.servings_min is not None and self.servings_min < 0:
            raise ValueError("Product servings_min cannot be negative.")
        if self.servings_max is not None and self.servings_max < 0:
            raise ValueError("Product servings_max cannot be negative.")
        if (
            self.servings_min is not None
            and self.servings_max is not None
            and self.servings_min > self.servings_max
        ):
            raise ValueError("Product servings_min cannot be greater than servings_max.")
        if not all(isinstance(allergen, str) for allergen in self.allergens):
            raise ValueError("Product allergens must contain strings.")
        object.__setattr__(self, "allergens", tuple(allergen.strip() for allergen in self.allergens if allergen.strip()))


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
    # Validate every row before returning a catalog so downstream search can assume valid products.
    with Path(path).open(newline="", encoding="utf-8") as catalog_file:
        reader = csv.DictReader(catalog_file)
        _validate_required_columns(reader.fieldnames)
        products = tuple(_product_from_row(row, row_number) for row_number, row in enumerate(reader, start=2))

    _validate_unique_ids(products)
    return products


def active_products(products: Iterable[Product]) -> tuple[Product, ...]:
    # Inactive products remain in the source data but must never be offered to customers.
    return tuple(product for product in products if product.active)


def search_exact_products(products: Iterable[Product], query: str) -> CatalogSearchResult:
    normalized_query = _normalize_text(query)
    if not normalized_query:
        return CatalogSearchResult(query=query, matches=())

    # Exact names and aliases are the highest-confidence matches.
    matches: list[CatalogMatch] = []
    for product in active_products(products):
        normalized_name = _normalize_text(product.name)
        if normalized_name == normalized_query:
            matches.append(CatalogMatch(product=product, match_type="exact_name", score=EXACT_MATCH_SCORE))
            continue

        normalized_aliases = {_normalize_text(alias) for alias in product.aliases}
        if normalized_query in normalized_aliases:
            matches.append(CatalogMatch(product=product, match_type="exact_alias", score=EXACT_MATCH_SCORE))

    return CatalogSearchResult(query=query, matches=tuple(matches))


def search_products(
    products: Iterable[Product],
    query: str,
    max_similarity_matches: int = 2,
) -> CatalogSearchResult:
    """Rank active catalog products with exact, partial, fuzzy, then category priority."""

    normalized_query = _normalize_text(query)
    if not normalized_query:
        return CatalogSearchResult(query=query, matches=())

    exact_result = search_exact_products(products, query)
    if exact_result.found:
        return exact_result

    matches = [
        match
        for product in active_products(products)
        if (match := _best_product_match(product, normalized_query)) is not None
    ]
    return CatalogSearchResult(query=query, matches=_order_matches(matches, max_similarity_matches))


def search_products_by_category(products: Iterable[Product], query: str) -> CatalogSearchResult:
    normalized_query = _normalize_text(query)
    if not normalized_query:
        return CatalogSearchResult(query=query, matches=())

    matches = tuple(
        CatalogMatch(product=product, match_type="category", score=CATEGORY_MATCH_SCORE)
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

    fuzzy_matches = [
        match
        for product in active_products(products)
        if (match := _best_fuzzy_match(product, normalized_query)) is not None
    ]
    return CatalogSearchResult(query=query, matches=_order_matches(fuzzy_matches, max_matches))


def _validate_required_columns(fieldnames: list[str] | None) -> None:
    if fieldnames is None:
        raise ValueError("Catalog CSV is empty.")

    missing_columns = [column for column in REQUIRED_CATALOG_COLUMNS if column not in fieldnames]
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise ValueError(f"Catalog CSV is missing required columns: {missing}.")


def _product_from_row(row: dict[str, str], row_number: int) -> Product:
    # Add the source row to parsing errors so catalog maintenance is actionable.
    try:
        return Product(
            id=row["id"].strip(),
            name=row["name"].strip(),
            aliases=_parse_aliases(row["aliases"]),
            category=row["category"].strip(),
            price=_parse_price(row["price"], row_number),
            active=_parse_active(row["active"], row_number),
            servings_min=_parse_optional_servings(row["servings_min"], "servings_min", row_number),
            servings_max=_parse_optional_servings(row["servings_max"], "servings_max", row_number),
            allergens=_parse_allergens(row["allergens"]),
        )
    except ValueError as error:
        raise ValueError(f"Invalid catalog row {row_number}: {error}") from error


def _parse_aliases(value: str) -> tuple[str, ...]:
    return _parse_pipe_delimited_strings(value)


def _parse_allergens(value: str) -> tuple[str, ...]:
    return _parse_pipe_delimited_strings(value)


def _parse_pipe_delimited_strings(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split("|") if item.strip())


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


def _parse_optional_servings(value: str, field: str, row_number: int) -> int | None:
    normalized = value.strip()
    if not normalized:
        return None
    try:
        return int(normalized)
    except ValueError as error:
        raise ValueError(f"{field} must be an integer in row {row_number}") from error


def _validate_unique_ids(products: tuple[Product, ...]) -> None:
    # Product IDs are stable references for cart items and persistence snapshots.
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
    # Search is accent-, punctuation-, and whitespace-insensitive while retaining display names.
    without_accents = "".join(
        character
        for character in unicodedata.normalize("NFD", value)
        if unicodedata.category(character) != "Mn"
    )
    normalized_spaces = re.sub(r"[\W_]+", " ", without_accents)
    return normalized_spaces.strip().lower()


def _best_product_match(product: Product, normalized_query: str) -> CatalogMatch | None:
    candidates = (
        ("name", _normalize_text(product.name)),
        *(("alias", _normalize_text(alias)) for alias in product.aliases),
    )
    matches = [
        match
        for source, candidate in candidates
        if (match := _candidate_match(product, normalized_query, source, candidate)) is not None
    ]
    category = _normalize_text(product.category)
    if normalized_query == category:
        matches.append(CatalogMatch(product=product, match_type="category", score=CATEGORY_MATCH_SCORE))
    return _select_best_match(matches)


def _candidate_match(
    product: Product,
    normalized_query: str,
    source: str,
    candidate: str,
) -> CatalogMatch | None:
    if normalized_query == candidate:
        return CatalogMatch(product=product, match_type=f"exact_{source}", score=EXACT_MATCH_SCORE)
    if _is_clear_partial_match(normalized_query, candidate):
        score = fuzz.partial_token_set_ratio(normalized_query, candidate) / 100
        return CatalogMatch(product=product, match_type=f"partial_{source}", score=score)
    if len(normalized_query) < MIN_FUZZY_QUERY_LENGTH:
        return None
    score = fuzz.WRatio(normalized_query, candidate)
    if score >= FUZZY_MATCH_THRESHOLD:
        return CatalogMatch(product=product, match_type=f"fuzzy_{source}", score=score / 100)
    return None


def _best_fuzzy_match(product: Product, normalized_query: str) -> CatalogMatch | None:
    matches = [
        match
        for source, candidate in (
            ("name", _normalize_text(product.name)),
            *(("alias", _normalize_text(alias)) for alias in product.aliases),
        )
        if (match := _fuzzy_candidate_match(product, normalized_query, source, candidate)) is not None
    ]
    return _select_best_match(matches)


def _fuzzy_candidate_match(
    product: Product,
    normalized_query: str,
    source: str,
    candidate: str,
) -> CatalogMatch | None:
    if len(normalized_query) < MIN_FUZZY_QUERY_LENGTH:
        return None
    score = fuzz.WRatio(normalized_query, candidate)
    if score < FUZZY_MATCH_THRESHOLD:
        return None
    return CatalogMatch(product=product, match_type=f"fuzzy_{source}", score=score / 100)


def _is_clear_partial_match(normalized_query: str, candidate: str) -> bool:
    if len(normalized_query) < MIN_PARTIAL_QUERY_LENGTH:
        return False
    if normalized_query in candidate:
        return fuzz.partial_token_set_ratio(normalized_query, candidate) >= PARTIAL_MATCH_THRESHOLD
    return set(normalized_query.split()).issubset(candidate.split())


def _select_best_match(matches: list[CatalogMatch]) -> CatalogMatch | None:
    return min(matches, key=_match_order_key) if matches else None


def _order_matches(matches: list[CatalogMatch], max_fuzzy_matches: int) -> tuple[CatalogMatch, ...]:
    ordered = sorted(matches, key=_match_order_key)
    if max_fuzzy_matches <= 0:
        return tuple(match for match in ordered if not match.match_type.startswith("fuzzy_"))

    fuzzy_count = 0
    limited: list[CatalogMatch] = []
    for match in ordered:
        if match.match_type.startswith("fuzzy_"):
            fuzzy_count += 1
            if fuzzy_count > max_fuzzy_matches:
                continue
        limited.append(match)
    return tuple(limited)


def _match_order_key(match: CatalogMatch) -> tuple[int, float, str, str]:
    return (
        MATCH_TYPE_PRIORITIES[match.match_type],
        -match.score,
        _normalize_text(match.product.name),
        match.product.id,
    )
