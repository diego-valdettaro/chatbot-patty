"""Tests for the channel-safe handoff boundary used by Streamlit."""

import pytest

from patty_bot.application.conversation_state import ConversationState, ConversationStatus, HandoffReason
from patty_bot.application.handoff_presentation import handoff_customer_message, locks_order_controls


@pytest.mark.parametrize("reason", tuple(HandoffReason))
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
