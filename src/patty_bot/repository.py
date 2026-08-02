import sqlite3
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path

from patty_bot.cart import Cart
from patty_bot.orders import ORDER_STATUS_PENDING, Order, OrderDetails, create_confirmed_order


def initialize_database(path: str | Path) -> None:
    # Schema setup is idempotent so the app and tools can call it before the first write.
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT NOT NULL,
                customer_phone TEXT NOT NULL,
                fulfillment_type TEXT NOT NULL,
                requested_date TEXT NOT NULL,
                delivery_address TEXT,
                pickup_store TEXT,
                subtotal TEXT NOT NULL,
                delivery_fee TEXT NOT NULL,
                total TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                product_id TEXT NOT NULL,
                product_name TEXT NOT NULL,
                unit_price TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                line_subtotal TEXT NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders(id)
            );
            """
        )


def save_confirmed_order(
    path: str | Path,
    cart: Cart,
    details: OrderDetails,
    reference_date: date | None = None,
) -> Order:
    # Build the immutable snapshot before writing so persistence receives a complete aggregate.
    order = create_confirmed_order(cart, details, reference_date=reference_date)
    return save_order(path, order)


def save_order(path: str | Path, order: Order) -> Order:
    """Persist a confirmed order and return the same aggregate with its database ID."""

    initialize_database(path)

    with sqlite3.connect(path) as connection:
        # The connection context commits both inserts together or rolls them back together on failure.
        connection.execute("PRAGMA foreign_keys = ON")
        cursor = connection.execute(
            """
            INSERT INTO orders (
                customer_name,
                customer_phone,
                fulfillment_type,
                requested_date,
                delivery_address,
                pickup_store,
                subtotal,
                delivery_fee,
                total,
                status,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                order.details.customer_name.strip(),
                order.details.customer_phone.strip(),
                order.details.fulfillment_type,
                order.details.requested_date.isoformat() if order.details.requested_date else "",
                order.details.delivery_address.strip() or None,
                order.details.pickup_store.strip() or None,
                _money(order.subtotal),
                _money(order.delivery_fee),
                _money(order.total),
                order.status,
                order.created_at.isoformat(timespec="seconds"),
            ),
        )
        order_id = cursor.lastrowid
        if order_id is None:
            raise RuntimeError("Could not create order.")

        # Store a product snapshot so historical orders do not change when the catalog changes later.
        connection.executemany(
            """
            INSERT INTO order_items (
                order_id,
                product_id,
                product_name,
                unit_price,
                quantity,
                line_subtotal
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                (
                    order_id,
                    item.product_id,
                    item.product_name,
                    _money(item.unit_price),
                    item.quantity,
                    _money(item.line_subtotal),
                )
                for item in order.items
            ),
        )

    # SQLite assigns the identity after insertion; the returned aggregate is the persisted order.
    return replace(order, id=order_id)


def _money(value: Decimal) -> str:
    # SQLite stores money as fixed decimal text to avoid binary floating-point rounding.
    return f"{value:.2f}"
