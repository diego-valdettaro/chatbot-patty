"""Deterministic policy for transferring a customer conversation to a person."""

import re
import unicodedata
from dataclasses import dataclass

from patty_bot.application.conversation_state import ConversationState, ConversationStatus, HandoffReason


@dataclass(frozen=True)
class HandoffDecision:
    """A typed, explainable decision to stop automatic handling."""

    reason: HandoffReason


_HUMAN_REQUEST_PATTERNS = (
    r"\bhablar con (una )?(persona|humano|asesor|agente|operador)\b",
    r"\batencion humana\b",
    r"\bquiero (una )?persona\b",
    r"\batender (un |una )?(persona|humano|asesor|agente|operador)\b",
)

_OUTSIDE_SCOPE_PATTERNS = (
    # Payments.
    r"\b(pago|pagar|tarjeta|transferencia|yape|plin)\b",
    # Real-time availability.
    r"\b(stock|disponible|disponibilidad|existencias|agotado)\b",
    # Allergens and dietary safety.
    r"\b(alerg\w*|gluten|lactosa)\b",
    # Commercial terms deliberately deferred from this MVP.
    r"\b(promo\w*|descuento|cupon\w*|oferta\w*)\b",
    # Opening and delivery/pickup hours.
    r"\b(horario\w*|abren|cierran|hora de (entrega|recojo))\b",
    # Business-to-business requests.
    r"\b(mayorista\w*|empresa\w*|corporativ\w*|b2b|factura|ruc)\b",
)

_UNRESOLVED_INPUTS = frozenset(
    {
        "?",
        "como",
        "cual",
        "no se",
        "no entiendo",
        "no comprendo",
        "ayuda",
    }
)


def decide_handoff(state: ConversationState, user_message: str) -> HandoffDecision | None:
    """Classify only explicit, safe-to-detect situations that require a person.

    This policy deliberately never asks an LLM to decide ownership.  It is run
    before provider setup so a selected handoff cannot spend a provider call or
    mutate an order through agent tools.
    """

    normalized = _normalize(user_message)
    if _matches_any(normalized, _HUMAN_REQUEST_PATTERNS):
        return HandoffDecision(HandoffReason.CUSTOMER_REQUEST)
    if state.status is ConversationStatus.CONFIRMED:
        return HandoffDecision(HandoffReason.OUTSIDE_SUPPORTED_SCOPE)
    if _matches_any(normalized, _OUTSIDE_SCOPE_PATTERNS):
        return HandoffDecision(HandoffReason.OUTSIDE_SUPPORTED_SCOPE)
    if _is_unresolved(normalized) and _has_prior_unresolved_input(state):
        return HandoffDecision(HandoffReason.UNRESOLVED_AMBIGUITY)
    return None


def _has_prior_unresolved_input(state: ConversationState) -> bool:
    return any(message.role == "user" and _is_unresolved(_normalize(message.content)) for message in state.messages)


def _is_unresolved(normalized_message: str) -> bool:
    return normalized_message in _UNRESOLVED_INPUTS


def _matches_any(message: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, message) is not None for pattern in patterns)


def _normalize(message: str) -> str:
    """Normalize Spanish text only for deterministic keyword matching."""

    accent_free = "".join(
        character
        for character in unicodedata.normalize("NFD", message.casefold())
        if unicodedata.category(character) != "Mn"
    )
    return re.sub(r"\s+", " ", accent_free.strip())
