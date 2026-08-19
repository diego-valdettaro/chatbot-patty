"""Channel-safe presentation rules for a human-owned conversation."""

from patty_bot.application.conversation_state import ConversationState, ConversationStatus, HandoffReason


_SAFE_HANDOFF_MESSAGES: dict[HandoffReason, str] = {
    HandoffReason.CUSTOMER_REQUEST: "Una persona del equipo continuará contigo en breve.",
    HandoffReason.REPEATED_UNRESOLVED_INPUT: "Una persona del equipo revisará tu pedido para entenderlo correctamente.",
    HandoffReason.UNRESOLVED_AMBIGUITY: "Una persona del equipo revisará los detalles para evitar errores en tu pedido.",
    HandoffReason.OUTSIDE_SUPPORTED_SCOPE: "Esta solicitud necesita la revisión de una persona del equipo.",
    HandoffReason.PROCESSING_ERROR: "Una persona del equipo continuará tu atención para ayudarte con seguridad.",
}

_FALLBACK_HANDOFF_MESSAGE = "Una persona del equipo continuará tu atención en breve."


def handoff_customer_message(state: ConversationState) -> str | None:
    """Return a helpful explanation without exposing internal reason values."""

    if state.status is not ConversationStatus.HUMAN_HANDOFF:
        return None
    return _SAFE_HANDOFF_MESSAGES.get(state.handoff_reason, _FALLBACK_HANDOFF_MESSAGE)


def locks_order_controls(state: ConversationState) -> bool:
    """Return whether this channel must render all ordering controls as read-only."""

    return state.status is ConversationStatus.HUMAN_HANDOFF or state.confirmed_order is not None
