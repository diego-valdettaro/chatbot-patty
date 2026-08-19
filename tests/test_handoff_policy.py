"""Focused tests for deterministic handoff classification."""

import pytest

from patty_bot.application.conversation_state import (
    ConversationMessage,
    ConversationState,
    ConversationStatus,
    HandoffReason,
)
from patty_bot.application.handoff_policy import decide_handoff


@pytest.mark.parametrize(
    "message",
    (
        "Quiero hablar con una persona.",
        "Necesito atencion humana.",
        "Me puede atender un asesor?",
    ),
)
def test_explicit_customer_request_has_priority(message: str) -> None:
    decision = decide_handoff(ConversationState(conversation_id="c-1"), message)

    assert decision is not None
    assert decision.reason is HandoffReason.CUSTOMER_REQUEST


@pytest.mark.parametrize(
    "message",
    (
        "Como pago?",
        "Hay stock disponible?",
        "Tiene gluten?",
        "Tienen algun descuento?",
        "Cual es su horario?",
        "Necesito una cotizacion mayorista para mi empresa.",
    ),
)
def test_outside_scope_requests_are_classified_without_an_llm(message: str) -> None:
    decision = decide_handoff(ConversationState(conversation_id="c-1"), message)

    assert decision is not None
    assert decision.reason is HandoffReason.OUTSIDE_SUPPORTED_SCOPE


def test_second_unresolved_input_is_classified_but_the_first_is_not() -> None:
    initial = ConversationState(conversation_id="c-1")
    after_first = ConversationState(
        conversation_id="c-1",
        messages=(ConversationMessage(role="user", content="No entiendo"),),
    )

    assert decide_handoff(initial, "No entiendo") is None
    decision = decide_handoff(after_first, "No se")
    assert decision is not None
    assert decision.reason is HandoffReason.UNRESOLVED_AMBIGUITY


def test_post_confirmation_message_is_sent_to_a_person() -> None:
    decision = decide_handoff(
        ConversationState(conversation_id="c-1", status=ConversationStatus.CONFIRMED),
        "Quiero cambiar el pedido.",
    )

    assert decision is not None
    assert decision.reason is HandoffReason.OUTSIDE_SUPPORTED_SCOPE


def test_regular_order_message_does_not_trigger_a_handoff() -> None:
    assert decide_handoff(ConversationState(conversation_id="c-1"), "Quiero dos brownies.") is None
