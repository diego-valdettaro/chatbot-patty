import sqlite3
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from patty_bot.cart import Cart, CartItem
from patty_bot.catalog import Product
from patty_bot.orders import OrderDetails
from patty_bot.repository import ORDER_STATUS_PENDING, initialize_database, save_confirmed_order


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

    order_id = save_confirmed_order(db_path, make_cart(), make_details(), reference_date=REFERENCE_DATE)

    with sqlite3.connect(db_path) as connection:
        order = connection.execute(
            """
            SELECT customer_name, customer_phone, fulfillment_type, requested_date,
                   delivery_address, pickup_store, subtotal, delivery_fee, total, status
            FROM orders
            WHERE id = ?
            """,
            (order_id,),
        ).fetchone()
        items = connection.execute(
            """
            SELECT product_id, product_name, unit_price, quantity, line_subtotal
            FROM order_items
            WHERE order_id = ?
            """,
            (order_id,),
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

    order_id = save_confirmed_order(db_path, make_cart(), details, reference_date=REFERENCE_DATE)

    with sqlite3.connect(db_path) as connection:
        order = connection.execute(
            "SELECT fulfillment_type, pickup_store, subtotal, delivery_fee, total FROM orders WHERE id = ?",
            (order_id,),
        ).fetchone()

    assert order == ("pickup", "San Isidro", "16.00", "0.00", "16.00")
