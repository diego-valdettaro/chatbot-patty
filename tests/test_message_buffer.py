"""Acceptance tests for the per-conversation message debounce buffer."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from patty_bot.agent.router import AgentTurn
from patty_bot.application.conversation_service import ConversationService, MESSAGE_DEBOUNCE_WINDOW
from patty_bot.application.conversation_state import ConversationStatus
from patty_bot.domain.catalog import load_catalog
from patty_bot.infrastructure.config import LLMSettings
from patty_bot.infrastructure.conversation_repository import SQLiteConversationRepository


SETTINGS = LLMSettings(
    provider="openai", model="test-model", api_key="test-key", langsmith_api_key="langsmith-test-key"
)


def service(tmp_path: Path) -> ConversationService:
    database_path = tmp_path / "conversations.sqlite3"
    return ConversationService(
        load_catalog(Path("data/catalog.sample.csv")), database_path, SQLiteConversationRepository(database_path)
    )


def configure_provider(monkeypatch, calls: list[tuple[str, tuple[dict[str, str], ...]]]) -> None:
    monkeypatch.setattr("patty_bot.application.conversation_service.load_llm_settings", lambda: SETTINGS)
    monkeypatch.setattr("patty_bot.application.conversation_service.create_openai_client", lambda _settings: object())

    def run_turn(_client, _settings, session, message, conversation):
        calls.append((message, conversation))
        return AgentTurn(reply="Gracias, ya lo anote.", session=session)

    monkeypatch.setattr("patty_bot.application.conversation_service.run_agent_turn", run_turn)


def test_messages_inside_the_sliding_window_make_one_ordered_agent_turn(tmp_path, monkeypatch) -> None:
    conversation_service = service(tmp_path)
    calls: list[tuple[str, tuple[dict[str, str], ...]]] = []
    configure_provider(monkeypatch, calls)
    start = datetime(2026, 8, 27, 15, 0, tzinfo=UTC)

    assert not conversation_service.queue_message("conversation-1", "Me llamo Diego", now=start)
    assert not conversation_service.queue_message("conversation-1", "Mi telefono es 95266383", now=start + timedelta(seconds=1))
    waiting = conversation_service.load_conversation("conversation-1")
    assert [message.content for message in waiting.pending_messages] == ["Me llamo Diego", "Mi telefono es 95266383"]
    assert conversation_service.process_due_messages("conversation-1", now=start + timedelta(seconds=3)) is None

    turn = conversation_service.process_due_messages("conversation-1", now=start + timedelta(seconds=4))

    assert turn is not None
    assert turn.reply == "Gracias, ya lo anote."
    assert calls == [("Me llamo Diego\nMi telefono es 95266383", ())]
    stored = conversation_service.load_conversation("conversation-1")
    assert [message.content for message in stored.messages] == [
        "Me llamo Diego",
        "Mi telefono es 95266383",
        "Gracias, ya lo anote.",
    ]
    assert not stored.pending_messages
    assert stored.processing_batch is None


def test_only_one_worker_can_claim_a_due_batch(tmp_path) -> None:
    conversation_service = service(tmp_path)
    start = datetime(2026, 8, 27, 15, 0, tzinfo=UTC)
    conversation_service.queue_message("conversation-1", "Hola", now=start)

    first_claim = conversation_service._repository.claim_pending_messages(
        "conversation-1", start + MESSAGE_DEBOUNCE_WINDOW
    )
    second_claim = conversation_service._repository.claim_pending_messages(
        "conversation-1", start + MESSAGE_DEBOUNCE_WINDOW
    )

    assert first_claim is not None
    assert [message.content for message in first_claim.processing_batch.messages] == ["Hola"]
    assert second_claim is None


def test_human_handoff_bypasses_the_window_and_retains_waiting_messages(tmp_path, monkeypatch) -> None:
    conversation_service = service(tmp_path)
    start = datetime(2026, 8, 27, 15, 0, tzinfo=UTC)
    monkeypatch.setattr(
        "patty_bot.application.conversation_service.load_llm_settings",
        lambda: pytest.fail("A human handoff must bypass the provider."),
    )

    conversation_service.queue_message("conversation-1", "Necesito una torta", now=start)
    assert conversation_service.queue_message("conversation-1", "Quiero hablar con una persona", now=start + timedelta(seconds=1))

    stored = conversation_service.load_conversation("conversation-1")
    assert stored.status is ConversationStatus.HUMAN_HANDOFF
    assert [message.content for message in stored.messages] == [
        "Necesito una torta",
        "Quiero hablar con una persona",
    ]
    assert not stored.pending_messages


def test_explicit_confirmation_bypasses_the_window(tmp_path, monkeypatch) -> None:
    conversation_service = service(tmp_path)
    calls: list[tuple[str, tuple[dict[str, str], ...]]] = []
    configure_provider(monkeypatch, calls)
    start = datetime(2026, 8, 27, 15, 0, tzinfo=UTC)

    conversation_service.queue_message("conversation-1", "Mi telefono es 95266383", now=start)
    assert conversation_service.queue_message("conversation-1", "Confirmo", now=start + timedelta(seconds=1))

    assert calls == [("Mi telefono es 95266383\nConfirmo", ())]
    assert not conversation_service.load_conversation("conversation-1").pending_messages


def test_provider_failure_keeps_claimed_messages_and_hands_off(tmp_path, monkeypatch) -> None:
    conversation_service = service(tmp_path)
    start = datetime(2026, 8, 27, 15, 0, tzinfo=UTC)
    monkeypatch.setattr("patty_bot.application.conversation_service.load_llm_settings", lambda: SETTINGS)
    monkeypatch.setattr("patty_bot.application.conversation_service.create_openai_client", lambda _settings: object())
    monkeypatch.setattr(
        "patty_bot.application.conversation_service.run_agent_turn",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("provider failed")),
    )

    conversation_service.queue_message("conversation-1", "Mi direccion es Lima", now=start)
    turn = conversation_service.process_due_messages("conversation-1", now=start + MESSAGE_DEBOUNCE_WINDOW)

    assert turn is not None
    stored = conversation_service.load_conversation("conversation-1")
    assert stored.status is ConversationStatus.HUMAN_HANDOFF
    assert [message.content for message in stored.messages] == [
        "Mi direccion es Lima",
        "Voy a derivar tu conversacion a una persona del equipo para que pueda ayudarte.",
    ]
    assert stored.processing_batch is None
