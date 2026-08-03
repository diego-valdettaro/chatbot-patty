"""Tests for the application boundary around the conversational agent."""

import logging
from pathlib import Path

from patty_bot.agent_router import AgentTurn
from patty_bot.catalog import load_catalog
from patty_bot.conversation import ConversationState
from patty_bot.conversation_repository import ConversationRepository
from patty_bot.config import LLMConfigurationError, LLMSettings
from patty_bot.conversation_service import ConversationService


SETTINGS = LLMSettings(
    provider="openai",
    model="test-model",
    api_key="test-key",
    langsmith_api_key="langsmith-test-key",
)


class InMemoryConversationRepository:
    def __init__(self) -> None:
        self.states: dict[str, ConversationState] = {}

    def load(self, conversation_id: str) -> ConversationState | None:
        return self.states.get(conversation_id)

    def save(self, conversation_state: ConversationState) -> None:
        self.states[conversation_state.conversation_id] = conversation_state


def service(repository: ConversationRepository) -> ConversationService:
    return ConversationService(
        load_catalog(Path("data/catalog.sample.csv")),
        Path("data/test-order.sqlite3"),
        repository,
    )


def test_handle_message_reuses_the_provider_client_and_returns_the_agent_turn(monkeypatch, caplog) -> None:
    repository = InMemoryConversationRepository()
    conversation_service = service(repository)
    client = object()
    calls = []
    monkeypatch.setattr("patty_bot.conversation_service.load_llm_settings", lambda: SETTINGS)
    monkeypatch.setattr("patty_bot.conversation_service.create_openai_client", lambda settings: client)

    def run_turn(received_client, settings, session, message, conversation):
        calls.append((received_client, settings, session, message, conversation))
        return AgentTurn(reply="Listo.", session=session)

    monkeypatch.setattr("patty_bot.conversation_service.run_agent_turn", run_turn)
    conversation_id = "conversation-1"
    caplog.set_level(logging.INFO, logger="patty_bot.conversation_service")

    first_turn = conversation_service.handle_message(conversation_id, "Hola")
    second_turn = conversation_service.handle_message(conversation_id, "Gracias")

    assert first_turn.reply == "Listo."
    assert second_turn.reply == "Listo."
    assert len(calls) == 2
    assert all(call[0] is client for call in calls)
    assert calls[1][4] == (
        {"role": "user", "content": "Hola"},
        {"role": "assistant", "content": "Listo."},
    )
    assert repository.states[conversation_id].messages[-2].content == "Gracias"
    assert repository.states[conversation_id].messages[-1].content == "Listo."
    assert "conversation turn started [conversation_id=conversation-1 stage=handle_message]" in caplog.text
    assert "agent execution started [conversation_id=conversation-1 stage=run_agent_turn]" in caplog.text
    assert "conversation persisted [conversation_id=conversation-1 stage=persist_turn]" in caplog.text


def test_handle_message_keeps_the_current_session_when_configuration_is_unavailable(monkeypatch, caplog) -> None:
    repository = InMemoryConversationRepository()
    conversation_service = service(repository)
    conversation_id = "conversation-1"
    monkeypatch.setattr(
        "patty_bot.conversation_service.load_llm_settings",
        lambda: (_ for _ in ()).throw(LLMConfigurationError("missing settings")),
    )
    caplog.set_level(logging.WARNING, logger="patty_bot.conversation_service")

    initial_state = conversation_service.load_conversation(conversation_id)
    turn = conversation_service.handle_message(conversation_id, "Hola")

    assert turn.session.cart == initial_state.cart
    assert turn.reply == "El chat con Patty aun no esta configurado. Completa las variables del LLM para activarlo."
    assert [message.content for message in repository.states[conversation_id].messages] == ["Hola", turn.reply]
    assert "LLM configuration unavailable [conversation_id=conversation-1 stage=load_settings]" in caplog.text


def test_new_conversation_leaves_the_requested_date_unset_until_the_customer_provides_it() -> None:
    repository = InMemoryConversationRepository()

    state = service(repository).load_conversation("conversation-1")

    assert state.order_details.requested_date is None


def test_unexpected_provider_errors_are_logged_and_translated_to_the_safe_reply(monkeypatch, caplog) -> None:
    repository = InMemoryConversationRepository()
    conversation_service = service(repository)
    monkeypatch.setattr("patty_bot.conversation_service.load_llm_settings", lambda: SETTINGS)
    monkeypatch.setattr("patty_bot.conversation_service.create_openai_client", lambda settings: object())
    monkeypatch.setattr(
        "patty_bot.conversation_service.run_agent_turn",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("provider internals")),
    )
    caplog.set_level(logging.ERROR, logger="patty_bot.conversation_service")

    turn = conversation_service.handle_message("conversation-1", "mensaje privado")

    assert turn.reply == "No pude responder en este momento. Intenta nuevamente en unos instantes."
    assert "agent provider error [conversation_id=conversation-1 stage=run_agent_turn error_type=RuntimeError]" in caplog.text
    assert "mensaje privado" not in caplog.text


def test_persistence_errors_are_logged_and_translated_to_the_safe_reply(caplog) -> None:
    class FailingConversationRepository:
        def load(self, conversation_id: str) -> ConversationState | None:
            raise OSError("database unavailable")

        def save(self, conversation_state: ConversationState) -> None:
            raise OSError("database unavailable")

    conversation_service = service(FailingConversationRepository())
    caplog.set_level(logging.ERROR, logger="patty_bot.conversation_service")

    turn = conversation_service.handle_message("conversation-1", "mensaje privado")

    assert turn.reply == "No pude responder en este momento. Intenta nuevamente en unos instantes."
    assert "conversation persistence error [conversation_id=conversation-1 stage=load_conversation error_type=OSError]" in caplog.text
    assert "mensaje privado" not in caplog.text
