import sqlite3
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from patty_bot.cart import Cart
from patty_bot.orders import OrderDetails, delivery_fee_for_order, total_for_order, validate_order_details


ORDER_STATUS_PENDING = "Pendiente de pago y revision"


def initialize_database(path: str | Path) -> None:
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
) -> int:
    _validate_confirmable_order(cart, details, reference_date)
    initialize_database(path)

    with sqlite3.connect(path) as connection:
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
                details.customer_name.strip(),
                details.customer_phone.strip(),
                details.fulfillment_type,
                details.requested_date.isoformat() if details.requested_date else "",
                details.delivery_address.strip() or None,
                details.pickup_store.strip() or None,
                _money(cart.subtotal),
                _money(delivery_fee_for_order(details)),
                _money(total_for_order(cart, details)),
                ORDER_STATUS_PENDING,
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        order_id = cursor.lastrowid
        if order_id is None:
            raise RuntimeError("Could not create order.")

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
                    item.product.id,
                    item.product.name,
                    _money(item.product.price),
                    item.quantity,
                    _money(item.line_subtotal),
                )
                for item in cart.items
            ),
        )

    return order_id


def _validate_confirmable_order(
    cart: Cart,
    details: OrderDetails,
    reference_date: date | None = None,
) -> None:
    if cart.is_empty:
        raise ValueError("Cannot confirm an empty cart.")

    validation = validate_order_details(details, reference_date=reference_date)
    if not validation.is_valid:
        problems = (*validation.missing_fields, *validation.invalid_fields)
        raise ValueError(f"Cannot confirm order with invalid details: {', '.join(problems)}")


def _money(value: Decimal) -> str:
    return f"{value:.2f}"
