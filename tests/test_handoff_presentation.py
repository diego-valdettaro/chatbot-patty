"""Tests for the channel-safe handoff boundary used by Streamlit."""

import pytest

from patty_bot.application.conversation_state import ConversationState, ConversationStatus, HandoffReason
from patty_bot.application.handoff_presentation import (
    HORECA_OR_SPECIAL_ORDER_HANDOFF_MESSAGE,
    handoff_customer_message,
    locks_order_controls,
)


@pytest.mark.parametrize("reason", tuple(reason for reason in HandoffReason if reason is not HandoffReason.HORECA_OR_SPECIAL_ORDER))
def test_handoff_uses_a_safe_customer_message_for_each_structured_reason(reason: HandoffReason) -> None:
    message = handoff_customer_message(
        ConversationState(
            conversation_id="handoff",
            status=ConversationStatus.HUMAN_HANDOFF,
            handoff_reason=reason,
        )
    )

    assert message is not None
    assert "persona del equipo" in message
    assert reason.value not in message


def test_horeca_and_special_orders_use_the_approved_customer_message() -> None:
    message = handoff_customer_message(
        ConversationState(
            conversation_id="handoff",
            status=ConversationStatus.HUMAN_HANDOFF,
            handoff_reason=HandoffReason.HORECA_OR_SPECIAL_ORDER,
        )
    )

    assert message == HORECA_OR_SPECIAL_ORDER_HANDOFF_MESSAGE
    assert message == (
        "Claro! Para pedidos HORECA o tortas especiales necesitamos revisarlo de forma personalizada. "
        "Te conecto con nuestro equipo para ayudarte con la cotización, diseño y disponibilidad."
    )


def test_handoff_without_a_reason_uses_a_safe_fallback_message() -> None:
    message = handoff_customer_message(
        ConversationState(conversation_id="handoff", status=ConversationStatus.HUMAN_HANDOFF)
    )

    assert message == "Una persona del equipo continuará tu atención en breve."


def test_only_handoff_has_a_customer_handoff_message() -> None:
    assert handoff_customer_message(ConversationState(conversation_id="active")) is None


def test_handoff_locks_order_controls_even_without_a_confirmed_order() -> None:
    handoff = ConversationState(
        conversation_id="handoff",
        status=ConversationStatus.HUMAN_HANDOFF,
        handoff_reason=HandoffReason.CUSTOMER_REQUEST,
    )

    assert locks_order_controls(handoff)
    assert not locks_order_controls(ConversationState(conversation_id="active"))
