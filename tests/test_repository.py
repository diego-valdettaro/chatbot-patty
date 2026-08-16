"""Persistence acceptance tests for SQLite orders and their item snapshots."""

import sqlite3
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from patty_bot.domain.cart import Cart, CartItem
from patty_bot.domain.catalog import Product
from patty_bot.application.conversation_state import ConversationState, ConversationStatus, HandoffReason
from patty_bot.domain.orders import OrderDetails
from patty_bot.infrastructure.conversation_repository import SQLiteConversationRepository
from patty_bot.infrastructure.repository import (
    ORDER_STATUS_PENDING,
    initialize_database,
    list_handoff_cases,
    list_orders,
    save_confirmed_order,
)


TMP_DIR = Path("tests/.tmp")
REFERENCE_DATE = date(2026, 7, 22)


def make_db_path(name: str) -> Path:
    TMP_DIR.mkdir(exist_ok=True)
    path = TMP_DIR / name
    if path.exists():
        path.unlink()
    return path


def make_product() -> Product:
    return Product(
        id="brownie-chocolate-belga",
        name="Brownie de chocolate belga",
        aliases=(),
        category="Brownies",
        price=Decimal("8.00"),
        active=True,
    )


def make_cart() -> Cart:
    return Cart(items=(CartItem(product=make_product(), quantity=2),))


def make_details() -> OrderDetails:
    return OrderDetails(
        customer_name="Diego",
        customer_phone="999999999",
        fulfillment_type="delivery",
        requested_date=date(2026, 7, 24),
        delivery_address="Av. Benavides 123",
    )


def test_initialize_database_creates_order_tables():
    db_path = make_db_path("schema.sqlite3")

    initialize_database(db_path)

    with sqlite3.connect(db_path) as connection:
        table_names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }

    assert {"orders", "order_items"}.issubset(table_names)


def test_save_confirmed_order_persists_order_and_items():
    db_path = make_db_path("save.sqlite3")

    confirmed_order = save_confirmed_order(db_path, make_cart(), make_details(), reference_date=REFERENCE_DATE)

    assert confirmed_order.id is not None
    assert confirmed_order.items[0].product_id == "brownie-chocolate-belga"
    assert confirmed_order.subtotal == Decimal("16.00")
    assert confirmed_order.total == Decimal("26.00")

    with sqlite3.connect(db_path) as connection:
        order = connection.execute(
            """
            SELECT customer_name, customer_phone, fulfillment_type, requested_date,
                   delivery_address, pickup_store, subtotal, delivery_fee, total, status
            FROM orders
            WHERE id = ?
            """,
            (confirmed_order.id,),
        ).fetchone()
        items = connection.execute(
            """
            SELECT product_id, product_name, unit_price, quantity, line_subtotal
            FROM order_items
            WHERE order_id = ?
            """,
            (confirmed_order.id,),
        ).fetchall()

    assert order == (
        "Diego",
        "999999999",
        "delivery",
        "2026-07-24",
        "Av. Benavides 123",
        None,
        "16.00",
        "10.00",
        "26.00",
        ORDER_STATUS_PENDING,
    )
    assert items == [("brownie-chocolate-belga", "Brownie de chocolate belga", "8.00", 2, "16.00")]


def test_save_confirmed_order_rejects_empty_cart():
    db_path = make_db_path("empty-cart.sqlite3")

    with pytest.raises(ValueError, match="empty cart"):
        save_confirmed_order(db_path, Cart(), make_details(), reference_date=REFERENCE_DATE)


def test_save_confirmed_order_rejects_invalid_details():
    db_path = make_db_path("invalid-details.sqlite3")
    details = OrderDetails(
        customer_name="",
        customer_phone="999999999",
        fulfillment_type="delivery",
        requested_date=date(2026, 7, 24),
        delivery_address="Av. Benavides 123",
    )

    with pytest.raises(ValueError, match="invalid details"):
        save_confirmed_order(db_path, make_cart(), details, reference_date=REFERENCE_DATE)


def test_save_confirmed_pickup_order_has_zero_delivery_fee():
    db_path = make_db_path("pickup.sqlite3")
    details = OrderDetails(
        customer_name="Diego",
        customer_phone="999999999",
        fulfillment_type="pickup",
        requested_date=date(2026, 7, 24),
        pickup_store="San Isidro",
    )

    confirmed_order = save_confirmed_order(db_path, make_cart(), details, reference_date=REFERENCE_DATE)

    assert confirmed_order.id is not None
    assert confirmed_order.delivery_fee == Decimal("0")

    with sqlite3.connect(db_path) as connection:
        order = connection.execute(
            "SELECT fulfillment_type, pickup_store, subtotal, delivery_fee, total FROM orders WHERE id = ?",
            (confirmed_order.id,),
        ).fetchone()

    assert order == ("pickup", "San Isidro", "16.00", "0.00", "16.00")


def test_list_orders_returns_confirmed_order_snapshots_for_a_future_dashboard():
    db_path = make_db_path("order-reader.sqlite3")
    saved_order = save_confirmed_order(db_path, make_cart(), make_details(), reference_date=REFERENCE_DATE)

    orders = list_orders(db_path)

    assert len(orders) == 1
    assert orders[0].id == saved_order.id
    assert orders[0].details == make_details()
    assert orders[0].total == Decimal("26.00")
    assert orders[0].items[0].product_name == "Brownie de chocolate belga"
    assert orders[0].items[0].unit_price == Decimal("8.00")


def test_list_handoff_cases_returns_only_structured_human_owned_conversations():
    db_path = make_db_path("handoff-reader.sqlite3")
    conversation_repository = SQLiteConversationRepository(db_path)
    conversation_repository.save(ConversationState(conversation_id="active", status=ConversationStatus.ACTIVE))
    conversation_repository.save(
        ConversationState(
            conversation_id="needs-human",
            status=ConversationStatus.HUMAN_HANDOFF,
            handoff_reason=HandoffReason.PROCESSING_ERROR,
        )
    )

    cases = list_handoff_cases(db_path)

    assert len(cases) == 1
    assert cases[0].conversation_id == "needs-human"
    assert cases[0].reason is HandoffReason.PROCESSING_ERROR
    assert cases[0].created_at.tzinfo is None
