"""Persistence tests for channel-independent conversation state."""

from datetime import date
from decimal import Decimal
from pathlib import Path

from patty_bot.cart import Cart, CartItem
from patty_bot.catalog import Product
from patty_bot.conversation import ConversationMessage, ConversationState, ConversationStatus
from patty_bot.conversation_repository import SQLiteConversationRepository
from patty_bot.orders import OrderDetails


def test_sqlite_repository_round_trips_the_state_required_for_the_next_turn(tmp_path) -> None:
    repository = SQLiteConversationRepository(tmp_path / "conversations.sqlite3")
    product = Product(
        id="brownie-chocolate-belga",
        name="Brownie de chocolate belga",
        aliases=("brownie",),
        category="Brownies",
        price=Decimal("8.00"),
        active=True,
    )
    state = ConversationState(
        conversation_id="web-session-1",
        status=ConversationStatus.AWAITING_CONFIRMATION,
        cart=Cart(items=(CartItem(product=product, quantity=2),)),
        order_details=OrderDetails(
            customer_name="Diego",
            customer_phone="999999999",
            requested_date=date(2026, 7, 24),
            delivery_address="Av. Benavides 123",
        ),
        messages=(
            ConversationMessage(role="user", content="Quiero brownies"),
            ConversationMessage(role="assistant", content="Listo."),
        ),
    )

    repository.save(state)

    assert repository.load("web-session-1") == state
    assert repository.load("missing") is None
