"""Tests for the small operational state model around free-form conversations."""

from dataclasses import replace
from pathlib import Path

import pytest

from patty_bot.catalog import load_catalog
from patty_bot.conversation import ConversationState, ConversationStatus, transition_status
from patty_bot.conversation_service import ConversationService
from patty_bot.orders import OrderDetails


class InMemoryConversationRepository:
    def __init__(self) -> None:
        self.states: dict[str, ConversationState] = {}

    def load(self, conversation_id: str) -> ConversationState | None:
        return self.states.get(conversation_id)

    def save(self, conversation_state: ConversationState) -> None:
        self.states[conversation_state.conversation_id] = conversation_state


def service(repository: InMemoryConversationRepository) -> ConversationService:
    return ConversationService(
        load_catalog(Path("data/catalog.sample.csv")),
        Path("data/test-order.sqlite3"),
        repository,
    )


@pytest.mark.parametrize(
    ("current", "target"),
    (
        (ConversationStatus.ACTIVE, ConversationStatus.AWAITING_CONFIRMATION),
        (ConversationStatus.AWAITING_CONFIRMATION, ConversationStatus.CONFIRMED),
        (ConversationStatus.AWAITING_CONFIRMATION, ConversationStatus.ACTIVE),
        (ConversationStatus.ACTIVE, ConversationStatus.HUMAN_HANDOFF),
        (ConversationStatus.ACTIVE, ConversationStatus.CANCELLED),
    ),
)
def test_operational_status_allows_expected_transitions(current, target) -> None:
    assert transition_status(current, target) is target


@pytest.mark.parametrize(
    ("current", "target"),
    (
        (ConversationStatus.ACTIVE, ConversationStatus.CONFIRMED),
        (ConversationStatus.CONFIRMED, ConversationStatus.ACTIVE),
        (ConversationStatus.HUMAN_HANDOFF, ConversationStatus.ACTIVE),
        (ConversationStatus.CANCELLED, ConversationStatus.ACTIVE),
    ),
)
def test_operational_status_rejects_invalid_transitions(current, target) -> None:
    with pytest.raises(ValueError, match="Invalid conversation status transition"):
        transition_status(current, target)


def test_confirmed_status_blocks_order_modifications() -> None:
    repository = InMemoryConversationRepository()
    conversation_service = service(repository)
    state = ConversationState(conversation_id="conversation-1", status=ConversationStatus.CONFIRMED)
    repository.save(state)

    with pytest.raises(ValueError, match="does not allow order modifications"):
        conversation_service.save_conversation(replace(state, order_details=OrderDetails(customer_name="Diego")))


def test_human_handoff_records_the_customer_message_without_running_the_agent(monkeypatch) -> None:
    repository = InMemoryConversationRepository()
    conversation_service = service(repository)
    conversation_id = "conversation-1"
    conversation_service.transition_conversation(conversation_id, ConversationStatus.HUMAN_HANDOFF)
    monkeypatch.setattr(
        "patty_bot.conversation_service.run_agent_turn",
        lambda *_args: pytest.fail("The automatic agent must not run during human handoff."),
    )

    turn = conversation_service.handle_message(conversation_id, "Necesito ayuda humana")

    assert turn.reply == ""
    assert repository.states[conversation_id].messages[-1].content == "Necesito ayuda humana"
