import sqlite3
from dataclasses import dataclass, replace
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from patty_bot.domain.cart import Cart
from patty_bot.domain.orders import ORDER_STATUS_PENDING, Order, OrderDetails, create_confirmed_order
from patty_bot.application.conversation_state import HandoffReason


@dataclass(frozen=True)
class StoredOrderItem:
    """Immutable item snapshot intended for administrative read models."""

    product_id: str
    product_name: str
    unit_price: Decimal
    quantity: int
    line_subtotal: Decimal


@dataclass(frozen=True)
class StoredOrder:
    """Confirmed order and its catalog snapshot, reconstructed from SQLite."""

    id: int
    details: OrderDetails
    subtotal: Decimal
    delivery_fee: Decimal
    total: Decimal
    status: str
    created_at: datetime
    items: tuple[StoredOrderItem, ...]


@dataclass(frozen=True)
class HandoffCase:
    """Minimal structured record a future operator dashboard can list safely."""

    conversation_id: str
    reason: HandoffReason
    created_at: datetime


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


def list_orders(path: str | Path) -> tuple[StoredOrder, ...]:
    """Read confirmed order snapshots without coupling a future dashboard to SQL."""

    initialize_database(path)
    with sqlite3.connect(path) as connection:
        order_rows = connection.execute(
            """
            SELECT id, customer_name, customer_phone, fulfillment_type, requested_date,
                   delivery_address, pickup_store, subtotal, delivery_fee, total, status, created_at
            FROM orders
            ORDER BY id DESC
            """
        ).fetchall()
        item_rows = connection.execute(
            """
            SELECT order_id, product_id, product_name, unit_price, quantity, line_subtotal
            FROM order_items
            ORDER BY id
            """
        ).fetchall()

    items_by_order: dict[int, list[StoredOrderItem]] = {}
    for order_id, product_id, product_name, unit_price, quantity, line_subtotal in item_rows:
        items_by_order.setdefault(order_id, []).append(
            StoredOrderItem(product_id, product_name, Decimal(unit_price), quantity, Decimal(line_subtotal))
        )
    return tuple(
        StoredOrder(
            id=order_id,
            details=OrderDetails(
                customer_name=customer_name,
                customer_phone=customer_phone,
                fulfillment_type=fulfillment_type,
                requested_date=date.fromisoformat(requested_date),
                delivery_address=delivery_address or "",
                pickup_store=pickup_store or "",
            ),
            subtotal=Decimal(subtotal),
            delivery_fee=Decimal(delivery_fee),
            total=Decimal(total),
            status=status,
            created_at=datetime.fromisoformat(created_at),
            items=tuple(items_by_order.get(order_id, [])),
        )
        for (
            order_id,
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
            created_at,
        ) in order_rows
    )


def list_handoff_cases(path: str | Path) -> tuple[HandoffCase, ...]:
    """List human-owned conversations and their structured operational reason."""

    from patty_bot.infrastructure.conversation_repository import SQLiteConversationRepository

    # Keep this public reader safe for a brand-new database and for legacy schemas.
    SQLiteConversationRepository(path)._initialize_schema()
    with sqlite3.connect(path) as connection:
        rows = connection.execute(
            """
            SELECT conversation_id, handoff_reason, handoff_created_at
            FROM conversations
            WHERE status = 'human_handoff' AND handoff_reason IS NOT NULL
            ORDER BY handoff_created_at DESC, conversation_id
            """
        ).fetchall()
    return tuple(
        HandoffCase(
            conversation_id=conversation_id,
            reason=HandoffReason(reason),
            created_at=datetime.fromisoformat(created_at),
        )
        for conversation_id, reason, created_at in rows
    )


def _money(value: Decimal) -> str:
    # SQLite stores money as fixed decimal text to avoid binary floating-point rounding.
    return f"{value:.2f}"
