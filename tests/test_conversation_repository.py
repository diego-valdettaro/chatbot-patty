"""Persistence tests for channel-independent conversation state."""

import sqlite3
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from patty_bot.domain.cart import Cart, CartItem
from patty_bot.domain.catalog import Product
from patty_bot.application.conversation_state import (
    ConversationMessage,
    ConversationState,
    ConversationStatus,
    HandoffReason,
)
from patty_bot.infrastructure.conversation_repository import SQLiteConversationRepository
from patty_bot.domain.orders import OrderDetails


def test_sqlite_repository_round_trips_the_state_required_for_the_next_turn(tmp_path) -> None:
    repository = SQLiteConversationRepository(tmp_path / "conversations.sqlite3")
    product = Product(
        id="brownie-chocolate-belga",
        name="Brownie de chocolate belga",
        aliases=("brownie",),
        category="Brownies",
        price=Decimal("8.00"),
        active=True,
        servings_min=1,
        servings_max=1,
        allergens=("nueces",),
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


def test_sqlite_repository_persists_a_structured_handoff_reason_for_operator_reads(tmp_path) -> None:
    database_path = tmp_path / "conversations.sqlite3"
    repository = SQLiteConversationRepository(database_path)
    state = ConversationState(
        conversation_id="web-session-2",
        status=ConversationStatus.HUMAN_HANDOFF,
        handoff_reason=HandoffReason.UNRESOLVED_AMBIGUITY,
    )

    repository.save(state)

    assert repository.load("web-session-2") == state
    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            "SELECT status, handoff_reason, handoff_created_at FROM conversations WHERE conversation_id = ?",
            ("web-session-2",),
        ).fetchone()
    assert row[:2] == ("human_handoff", "unresolved_ambiguity")
    assert row[2] is not None


def test_sqlite_repository_rejects_an_unexplained_handoff_before_writing(tmp_path) -> None:
    repository = SQLiteConversationRepository(tmp_path / "conversations.sqlite3")

    with pytest.raises(ValueError, match="require a HandoffReason"):
        repository.save(
            ConversationState(conversation_id="web-session-3", status=ConversationStatus.HUMAN_HANDOFF)
        )


def test_sqlite_repository_migrates_an_existing_conversations_table_additively(tmp_path) -> None:
    database_path = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE conversations (
                conversation_id TEXT PRIMARY KEY,
                cart_json TEXT NOT NULL,
                order_details_json TEXT NOT NULL,
                confirmed_order_json TEXT,
                messages_json TEXT NOT NULL
            )
            """
        )

    SQLiteConversationRepository(database_path).load("missing")

    with sqlite3.connect(database_path) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(conversations)")}
    assert {"status", "handoff_reason", "handoff_created_at"}.issubset(columns)
