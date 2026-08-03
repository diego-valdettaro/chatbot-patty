"""State objects required to continue a customer conversation across channels."""

from dataclasses import dataclass
from enum import Enum

from patty_bot.domain.cart import Cart
from patty_bot.domain.orders import Order, OrderDetails


class ConversationStatus(str, Enum):
    """Operational status that limits actions without prescribing conversation content."""

    ACTIVE = "active"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    CONFIRMED = "confirmed"
    HUMAN_HANDOFF = "human_handoff"
    CANCELLED = "cancelled"


_ALLOWED_TRANSITIONS: dict[ConversationStatus, frozenset[ConversationStatus]] = {
    ConversationStatus.ACTIVE: frozenset(
        {
            ConversationStatus.AWAITING_CONFIRMATION,
            ConversationStatus.HUMAN_HANDOFF,
            ConversationStatus.CANCELLED,
        }
    ),
    ConversationStatus.AWAITING_CONFIRMATION: frozenset(
        {
            ConversationStatus.ACTIVE,
            ConversationStatus.CONFIRMED,
            ConversationStatus.HUMAN_HANDOFF,
            ConversationStatus.CANCELLED,
        }
    ),
    ConversationStatus.CONFIRMED: frozenset(),
    ConversationStatus.HUMAN_HANDOFF: frozenset(),
    ConversationStatus.CANCELLED: frozenset(),
}


@dataclass(frozen=True)
class ConversationMessage:
    """One customer-visible message retained as short conversational context."""

    role: str
    content: str


@dataclass(frozen=True)
class ConversationState:
    """Persisted state for one active customer conversation without application logic."""

    conversation_id: str
    status: ConversationStatus = ConversationStatus.ACTIVE
    cart: Cart = Cart()
    order_details: OrderDetails = OrderDetails()
    confirmed_order: Order | None = None
    messages: tuple[ConversationMessage, ...] = ()


def transition_status(current: ConversationStatus, target: ConversationStatus) -> ConversationStatus:
    """Validate a small operational transition without constraining natural-language turns."""

    if target == current:
        return current
    if target not in _ALLOWED_TRANSITIONS[current]:
        raise ValueError(f"Invalid conversation status transition: {current.value} -> {target.value}.")
    return target


def allows_order_modification(status: ConversationStatus) -> bool:
    """Return whether channel controls and agent tools may change the draft order."""

    return status in {ConversationStatus.ACTIVE, ConversationStatus.AWAITING_CONFIRMATION}


def allows_automatic_response(status: ConversationStatus) -> bool:
    """Keep a human-owned or cancelled conversation out of the automatic agent path."""

    return status not in {ConversationStatus.HUMAN_HANDOFF, ConversationStatus.CANCELLED}
