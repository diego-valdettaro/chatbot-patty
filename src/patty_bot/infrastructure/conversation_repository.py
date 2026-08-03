"""SQLite persistence boundary for channel-independent conversation state."""

import json
import sqlite3
from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Protocol

from patty_bot.domain.cart import Cart, CartItem
from patty_bot.domain.catalog import Product
from patty_bot.application.conversation_state import ConversationMessage, ConversationState, ConversationStatus
from patty_bot.domain.orders import Order, OrderDetails, OrderItem


class ConversationRepository(Protocol):
    """Storage contract so a future channel backend is not coupled to SQLite."""

    def load(self, conversation_id: str) -> ConversationState | None:
        """Return persisted state, if the conversation has already started."""

    def save(self, conversation_state: ConversationState) -> None:
        """Persist the complete state needed to resume a conversation."""


class SQLiteConversationRepository:
    """Persist complete conversation aggregates in the existing local SQLite database."""

    def __init__(self, database_path: str | Path) -> None:
        self._database_path = Path(database_path)

    def load(self, conversation_id: str) -> ConversationState | None:
        self._initialize_schema()
        with sqlite3.connect(self._database_path) as connection:
            row = connection.execute(
                """
                SELECT status, cart_json, order_details_json, confirmed_order_json, messages_json
                FROM conversations
                WHERE conversation_id = ?
                """,
                (conversation_id,),
            ).fetchone()
        if row is None:
            return None
        return ConversationState(
            conversation_id=conversation_id,
            status=ConversationStatus(row[0]),
            cart=_cart_from_data(_json_object(row[1])),
            order_details=_order_details_from_data(_json_object(row[2])),
            confirmed_order=_order_from_data(_json_object(row[3])) if row[3] is not None else None,
            messages=tuple(_message_from_data(item) for item in _json_list(row[4])),
        )

    def save(self, conversation_state: ConversationState) -> None:
        self._initialize_schema()
        with sqlite3.connect(self._database_path) as connection:
            connection.execute(
                """
                INSERT INTO conversations (
                    conversation_id, status, cart_json, order_details_json, confirmed_order_json, messages_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(conversation_id) DO UPDATE SET
                    status = excluded.status,
                    cart_json = excluded.cart_json,
                    order_details_json = excluded.order_details_json,
                    confirmed_order_json = excluded.confirmed_order_json,
                    messages_json = excluded.messages_json
                """,
                (
                    conversation_state.conversation_id,
                    conversation_state.status.value,
                    _to_json(_cart_to_data(conversation_state.cart)),
                    _to_json(_order_details_to_data(conversation_state.order_details)),
                    _to_json(_order_to_data(conversation_state.confirmed_order))
                    if conversation_state.confirmed_order is not None
                    else None,
                    _to_json([_message_to_data(message) for message in conversation_state.messages]),
                ),
            )

    def _initialize_schema(self) -> None:
        # The aggregate is serialized together so loading it always produces one coherent turn state.
        with sqlite3.connect(self._database_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    conversation_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL DEFAULT 'active',
                    cart_json TEXT NOT NULL,
                    order_details_json TEXT NOT NULL,
                    confirmed_order_json TEXT,
                    messages_json TEXT NOT NULL
                )
                """
            )
            columns = {row[1] for row in connection.execute("PRAGMA table_info(conversations)")}
            if "status" not in columns:
                # Existing local databases retain their active conversations during this additive migration.
                connection.execute("ALTER TABLE conversations ADD COLUMN status TEXT NOT NULL DEFAULT 'active'")


def _to_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _json_object(raw_value: str) -> Mapping[str, Any]:
    value = json.loads(raw_value)
    if not isinstance(value, dict):
        raise ValueError("Conversation state must contain JSON objects.")
    return value


def _json_list(raw_value: str) -> list[Mapping[str, Any]]:
    value = json.loads(raw_value)
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError("Conversation messages must be a JSON array of objects.")
    return value


def _cart_to_data(cart: Cart) -> dict[str, object]:
    return {"items": [{"product": _product_to_data(item.product), "quantity": item.quantity} for item in cart.items]}


def _cart_from_data(data: Mapping[str, Any]) -> Cart:
    raw_items = data.get("items", [])
    if not isinstance(raw_items, list):
        raise ValueError("Conversation cart items must be a list.")
    return Cart(
        items=tuple(
            CartItem(product=_product_from_data(item["product"]), quantity=item["quantity"])
            for item in raw_items
            if isinstance(item, dict)
        )
    )


def _product_to_data(product: Product) -> dict[str, object]:
    return {
        "id": product.id,
        "name": product.name,
        "aliases": list(product.aliases),
        "category": product.category,
        "price": str(product.price),
        "active": product.active,
        "servings_min": product.servings_min,
        "servings_max": product.servings_max,
        "allergens": list(product.allergens),
    }


def _product_from_data(data: object) -> Product:
    if not isinstance(data, dict):
        raise ValueError("Conversation cart product must be an object.")
    return Product(
        id=data["id"],
        name=data["name"],
        aliases=tuple(data["aliases"]),
        category=data["category"],
        price=Decimal(data["price"]),
        active=data["active"],
        servings_min=data.get("servings_min"),
        servings_max=data.get("servings_max"),
        allergens=tuple(data.get("allergens", [])),
    )


def _order_details_to_data(details: OrderDetails) -> dict[str, object]:
    return {
        "customer_name": details.customer_name,
        "customer_phone": details.customer_phone,
        "fulfillment_type": details.fulfillment_type,
        "requested_date": details.requested_date.isoformat() if details.requested_date else None,
        "delivery_address": details.delivery_address,
        "pickup_store": details.pickup_store,
    }


def _order_details_from_data(data: Mapping[str, Any]) -> OrderDetails:
    requested_date = data.get("requested_date")
    return OrderDetails(
        customer_name=data["customer_name"],
        customer_phone=data["customer_phone"],
        fulfillment_type=data["fulfillment_type"],
        requested_date=date.fromisoformat(requested_date) if requested_date else None,
        delivery_address=data["delivery_address"],
        pickup_store=data["pickup_store"],
    )


def _order_to_data(order: Order) -> dict[str, object]:
    return {
        "details": _order_details_to_data(order.details),
        "items": [
            {
                "product_id": item.product_id,
                "product_name": item.product_name,
                "unit_price": str(item.unit_price),
                "quantity": item.quantity,
                "line_subtotal": str(item.line_subtotal),
            }
            for item in order.items
        ],
        "subtotal": str(order.subtotal),
        "delivery_fee": str(order.delivery_fee),
        "total": str(order.total),
        "status": order.status,
        "created_at": order.created_at.isoformat(),
        "id": order.id,
    }


def _order_from_data(data: Mapping[str, Any]) -> Order:
    raw_items = data.get("items", [])
    if not isinstance(raw_items, list):
        raise ValueError("Confirmed order items must be a list.")
    return Order(
        details=_order_details_from_data(data["details"]),
        items=tuple(
            OrderItem(
                product_id=item["product_id"],
                product_name=item["product_name"],
                unit_price=Decimal(item["unit_price"]),
                quantity=item["quantity"],
                line_subtotal=Decimal(item["line_subtotal"]),
            )
            for item in raw_items
            if isinstance(item, dict)
        ),
        subtotal=Decimal(data["subtotal"]),
        delivery_fee=Decimal(data["delivery_fee"]),
        total=Decimal(data["total"]),
        status=data["status"],
        created_at=datetime.fromisoformat(data["created_at"]),
        id=data["id"],
    )


def _message_to_data(message: ConversationMessage) -> dict[str, str]:
    return {"role": message.role, "content": message.content}


def _message_from_data(data: Mapping[str, Any]) -> ConversationMessage:
    return ConversationMessage(role=data["role"], content=data["content"])
