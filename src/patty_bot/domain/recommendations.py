"""Deterministic catalog recommendations based on structured customer needs."""

from dataclasses import dataclass
from decimal import Decimal
import re
import unicodedata
from typing import Iterable

from patty_bot.domain.catalog import Product


CATEGORY_MATCH_SCORE = 30
SERVINGS_MATCH_SCORE = 50
WITHIN_BUDGET_SCORE = 20


@dataclass(frozen=True)
class RecommendationRequest:
    category: str | None = None
    servings: int | None = None
    excluded_allergens: tuple[str, ...] = ()
    max_price: Decimal | None = None

    def __post_init__(self) -> None:
        if self.servings is not None and self.servings < 0:
            raise ValueError("Recommendation servings cannot be negative.")
        if self.max_price is not None and self.max_price < Decimal("0"):
            raise ValueError("Recommendation max_price cannot be negative.")

        normalized_allergens: list[str] = []
        for allergen in self.excluded_allergens:
            if not isinstance(allergen, str):
                raise ValueError("Recommendation excluded_allergens must contain strings.")
            normalized = _normalize_text(allergen)
            if not normalized:
                raise ValueError("Recommendation excluded_allergens cannot contain empty strings.")
            normalized_allergens.append(normalized)
        object.__setattr__(self, "excluded_allergens", tuple(normalized_allergens))


@dataclass(frozen=True)
class RecommendedProduct:
    product: Product
    score: int
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class RecommendationResult:
    recommendations: tuple[RecommendedProduct, ...]


class RecommendationService:
    """Ranks compatible products without side effects or external dependencies."""

    def __init__(self, products: Iterable[Product]) -> None:
        self._products = tuple(products)

    def recommend(self, request: RecommendationRequest) -> RecommendationResult:
        recommendations = [
            recommendation
            for product in self._products
            if (recommendation := self._recommend_product(product, request)) is not None
        ]
        ordered = sorted(
            recommendations,
            key=lambda recommendation: (
                -recommendation.score,
                _normalize_text(recommendation.product.name),
                recommendation.product.id,
            ),
        )
        return RecommendationResult(recommendations=tuple(ordered))

    def _recommend_product(
        self,
        product: Product,
        request: RecommendationRequest,
    ) -> RecommendedProduct | None:
        if not product.active:
            return None
        if _has_excluded_allergen(product, request.excluded_allergens):
            return None
        # Budget is intentionally a hard constraint in this first version.
        if request.max_price is not None and product.price > request.max_price:
            return None

        score = 0
        reasons: list[str] = []
        if request.category is not None and _normalize_text(product.category) == _normalize_text(request.category):
            score += CATEGORY_MATCH_SCORE
            reasons.append("category_match")
        if request.servings is not None and _covers_servings(product, request.servings):
            score += SERVINGS_MATCH_SCORE
            reasons.append("servings_match")
        if request.max_price is not None:
            score += WITHIN_BUDGET_SCORE
            reasons.append("within_budget")

        return RecommendedProduct(product=product, score=score, reasons=tuple(reasons))


def _has_excluded_allergen(product: Product, excluded_allergens: tuple[str, ...]) -> bool:
    product_allergens = {_normalize_text(allergen) for allergen in product.allergens}
    return bool(product_allergens.intersection(excluded_allergens))


def _covers_servings(product: Product, servings: int) -> bool:
    if product.servings_min is None or product.servings_max is None:
        return False
    return product.servings_min <= servings <= product.servings_max


def _normalize_text(value: str) -> str:
    without_accents = "".join(
        character
        for character in unicodedata.normalize("NFD", value)
        if unicodedata.category(character) != "Mn"
    )
    return re.sub(r"\s+", " ", without_accents).strip().lower()
