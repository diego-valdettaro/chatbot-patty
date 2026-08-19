"""Focused Streamlit boundary tests for a human-owned conversation."""

from types import SimpleNamespace

import app

from patty_bot.application.conversation_state import (
    ConversationMessage,
    ConversationState,
    ConversationStatus,
    HandoffReason,
)


class _Context:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class FakeStreamlit:
    def __init__(self, state: ConversationState) -> None:
        self.session_state = SimpleNamespace(conversation_state=state)
        self.chat_input_calls: list[tuple[str, bool]] = []
        self.warnings: list[str] = []
        self.writes: list[str] = []

    def subheader(self, _label: str) -> None:
        pass

    def caption(self, _label: str) -> None:
        pass

    def warning(self, label: str) -> None:
        self.warnings.append(label)

    def container(self, **_kwargs):
        return _Context()

    def chat_message(self, _role: str):
        return _Context()

    def write(self, value: str) -> None:
        self.writes.append(value)

    def chat_input(self, label: str, *, disabled: bool):
        self.chat_input_calls.append((label, disabled))
        return None


def test_handoff_renders_safe_status_and_retains_customer_messages(monkeypatch) -> None:
    state = ConversationState(
        conversation_id="handoff",
        status=ConversationStatus.HUMAN_HANDOFF,
        handoff_reason=HandoffReason.CUSTOMER_REQUEST,
        messages=(
            ConversationMessage(role="assistant", content="¿Cómo puedo ayudarte?"),
            ConversationMessage(role="user", content="Necesito que una persona me responda."),
        ),
    )
    streamlit = FakeStreamlit(state)
    monkeypatch.setattr(app, "st", streamlit)

    app.render_chat()

    assert streamlit.chat_input_calls == [("Escribe un mensaje para Patty", True)]
    assert len(streamlit.warnings) == 1
    assert "está siendo atendida por una persona" in streamlit.warnings[0]
    assert streamlit.writes == ["¿Cómo puedo ayudarte?", "Necesito que una persona me responda."]
