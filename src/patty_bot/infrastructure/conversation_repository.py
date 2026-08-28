"""SQLite persistence boundary for channel-independent conversation state."""

import json
import sqlite3
from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Protocol

from patty_bot.domain.cart import Cart, CartItem
from patty_bot.domain.catalog import Product
from patty_bot.application.conversation_state import (
    ConversationMessage,
    PendingMessage,
    PendingMessageBatch,
    ConversationState,
    ConversationStatus,
    HandoffReason,
)
from patty_bot.domain.orders import Order, OrderDetails, OrderItem
from patty_bot.application.errors import ConversationStateCorruptionError


class ConversationRepository(Protocol):
    """Storage contract so a future channel backend is not coupled to SQLite."""

    def load(self, conversation_id: str) -> ConversationState | None:
        """Return persisted state, if the conversation has already started."""

    def save(self, conversation_state: ConversationState) -> None:
        """Persist the complete state needed to resume a conversation."""

    def enqueue_pending_message(self, conversation_id: str, message: PendingMessage, pending_until: datetime) -> ConversationState:
        """Append one message and reset its debounce deadline atomically."""

    def claim_pending_messages(self, conversation_id: str, now: datetime, *, force: bool = False) -> ConversationState | None:
        """Claim due messages so at most one worker invokes the provider."""

    def complete_pending_messages(
        self, conversation_id: str, batch_id: str, reply: str, state: ConversationState
    ) -> ConversationState:
        """Persist one claimed batch and its reply without dropping newer pending messages."""

    def handoff_pending_messages(
        self, conversation_id: str, user_message: str, reason: HandoffReason
    ) -> ConversationState:
        """Atomically retain waiting input before assigning the conversation to a person."""


class SQLiteConversationRepository:
    """Persist complete conversation aggregates in the existing local SQLite database."""

    def __init__(self, database_path: str | Path) -> None:
        self._database_path = Path(database_path)

    def load(self, conversation_id: str) -> ConversationState | None:
        self._initialize_schema()
        with sqlite3.connect(self._database_path) as connection:
            row = connection.execute(
                """
                SELECT status, cart_json, order_details_json, confirmed_order_json, messages_json, handoff_reason,
                       pending_messages_json, pending_until, processing_batch_json
                FROM conversations
                WHERE conversation_id = ?
                """,
                (conversation_id,),
            ).fetchone()
        if row is None:
            return None
        try:
            state = _state_from_row(conversation_id, row)
            _validate_loaded_state(state)
            return state
        except (InvalidOperation, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            # Do not overwrite a malformed row with an empty state.  Callers can
            # present a safe reply while the original row remains available for
            # diagnosis and recovery.
            raise ConversationStateCorruptionError("Persisted conversation state is invalid.") from error

    def save(self, conversation_state: ConversationState) -> None:
        self._initialize_schema()
        with sqlite3.connect(self._database_path) as connection:
            _save_with_connection(connection, conversation_state)

    def enqueue_pending_message(self, conversation_id: str, message: PendingMessage, pending_until: datetime) -> ConversationState:
        self._initialize_schema()
        with sqlite3.connect(self._database_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = _conversation_row(connection, conversation_id)
            state = _state_from_row(conversation_id, row) if row is not None else ConversationState(conversation_id=conversation_id)
            if state.processing_batch is not None and any(item.id == message.id for item in state.processing_batch.messages):
                return state
            if any(item.id == message.id for item in state.pending_messages):
                return state
            updated = ConversationState(
                conversation_id=state.conversation_id, status=state.status, cart=state.cart, order_details=state.order_details,
                confirmed_order=state.confirmed_order, messages=state.messages, handoff_reason=state.handoff_reason,
                pending_messages=state.pending_messages + (message,), pending_until=pending_until,
                processing_batch=state.processing_batch,
            )
            _save_with_connection(connection, updated)
            return updated

    def claim_pending_messages(self, conversation_id: str, now: datetime, *, force: bool = False) -> ConversationState | None:
        self._initialize_schema()
        with sqlite3.connect(self._database_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = _conversation_row(connection, conversation_id)
            if row is None:
                return None
            state = _state_from_row(conversation_id, row)
            if state.processing_batch is not None or not state.pending_messages:
                return None
            if not force and (state.pending_until is None or now < state.pending_until):
                return None
            batch = PendingMessageBatch(id=state.pending_messages[0].id, messages=state.pending_messages)
            claimed = ConversationState(
                conversation_id=state.conversation_id, status=state.status, cart=state.cart, order_details=state.order_details,
                confirmed_order=state.confirmed_order, messages=state.messages, handoff_reason=state.handoff_reason,
                processing_batch=batch,
            )
            _save_with_connection(connection, claimed)
            return claimed

    def complete_pending_messages(self, conversation_id: str, batch_id: str, reply: str, state: ConversationState) -> ConversationState:
        self._initialize_schema()
        with sqlite3.connect(self._database_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = _conversation_row(connection, conversation_id)
            if row is None:
                raise ValueError("Cannot complete a missing conversation.")
            current = _state_from_row(conversation_id, row)
            if current.processing_batch is None or current.processing_batch.id != batch_id:
                raise ValueError("Pending message batch is no longer claimed by this worker.")
            completed = ConversationState(
                conversation_id=current.conversation_id, status=state.status, cart=state.cart, order_details=state.order_details,
                confirmed_order=state.confirmed_order,
                messages=current.messages + tuple(ConversationMessage(role="user", content=item.content) for item in current.processing_batch.messages)
                + (ConversationMessage(role="assistant", content=reply),),
                handoff_reason=state.handoff_reason, pending_messages=current.pending_messages,
                pending_until=current.pending_until,
            )
            _save_with_connection(connection, completed)
            return completed

    def handoff_pending_messages(
        self, conversation_id: str, user_message: str, reason: HandoffReason
    ) -> ConversationState:
        self._initialize_schema()
        with sqlite3.connect(self._database_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = _conversation_row(connection, conversation_id)
            if row is None:
                raise ValueError("Cannot hand off a missing conversation.")
            state = _state_from_row(conversation_id, row)
            waiting = state.pending_messages
            if state.processing_batch is not None:
                waiting = state.processing_batch.messages + waiting
            handed_off = ConversationState(
                conversation_id=state.conversation_id,
                status=ConversationStatus.HUMAN_HANDOFF,
                cart=state.cart,
                order_details=state.order_details,
                confirmed_order=state.confirmed_order,
                messages=state.messages
                + tuple(ConversationMessage(role="user", content=item.content) for item in waiting)
                + (ConversationMessage(role="user", content=user_message),),
                handoff_reason=reason,
            )
            _save_with_connection(connection, handed_off)
            return handed_off

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
                    messages_json TEXT NOT NULL,
                    handoff_reason TEXT,
                    handoff_created_at TEXT,
                    pending_messages_json TEXT NOT NULL DEFAULT '[]',
                    pending_until TEXT,
                    processing_batch_json TEXT
                )
                """
            )
            columns = {row[1] for row in connection.execute("PRAGMA table_info(conversations)")}
            if "status" not in columns:
                # Existing local databases retain their active conversations during this additive migration.
                connection.execute("ALTER TABLE conversations ADD COLUMN status TEXT NOT NULL DEFAULT 'active'")
            if "handoff_reason" not in columns:
                connection.execute("ALTER TABLE conversations ADD COLUMN handoff_reason TEXT")
            if "handoff_created_at" not in columns:
                connection.execute("ALTER TABLE conversations ADD COLUMN handoff_created_at TEXT")
            if "pending_messages_json" not in columns:
                connection.execute("ALTER TABLE conversations ADD COLUMN pending_messages_json TEXT NOT NULL DEFAULT '[]'")
            if "pending_until" not in columns:
                connection.execute("ALTER TABLE conversations ADD COLUMN pending_until TEXT")
            if "processing_batch_json" not in columns:
                connection.execute("ALTER TABLE conversations ADD COLUMN processing_batch_json TEXT")


def _handoff_reason_to_value(conversation_state: ConversationState) -> str | None:
    """Return the structured reason only for a human-owned conversation."""

    if conversation_state.status is ConversationStatus.HUMAN_HANDOFF:
        if conversation_state.handoff_reason is None:
            raise ValueError("Human handoff conversations require a HandoffReason before persistence.")
        return conversation_state.handoff_reason.value
    if conversation_state.handoff_reason is not None:
        raise ValueError("Only human handoff conversations may persist a HandoffReason.")
    return None


def _conversation_row(connection: sqlite3.Connection, conversation_id: str) -> tuple[object, ...] | None:
    return connection.execute(
        """
        SELECT status, cart_json, order_details_json, confirmed_order_json, messages_json, handoff_reason,
               pending_messages_json, pending_until, processing_batch_json
        FROM conversations WHERE conversation_id = ?
        """,
        (conversation_id,),
    ).fetchone()


def _state_from_row(conversation_id: str, row: tuple[object, ...]) -> ConversationState:
    processing_batch = _pending_batch_from_data(_json_object(row[8])) if row[8] is not None else None
    return ConversationState(
        conversation_id=conversation_id,
        status=ConversationStatus(row[0]),
        cart=_cart_from_data(_json_object(row[1])),
        order_details=_order_details_from_data(_json_object(row[2])),
        confirmed_order=_order_from_data(_json_object(row[3])) if row[3] is not None else None,
        messages=tuple(_message_from_data(item) for item in _json_list(row[4])),
        handoff_reason=HandoffReason(row[5]) if row[5] is not None else None,
        pending_messages=tuple(_pending_message_from_data(item) for item in _json_list(row[6])),
        pending_until=datetime.fromisoformat(row[7]) if row[7] is not None else None,
        processing_batch=processing_batch,
    )


def _save_with_connection(connection: sqlite3.Connection, conversation_state: ConversationState) -> None:
    connection.execute(
        """
        INSERT INTO conversations (
            conversation_id, status, cart_json, order_details_json, confirmed_order_json, messages_json,
            handoff_reason, handoff_created_at, pending_messages_json, pending_until, processing_batch_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, CASE WHEN ? IS NULL THEN NULL ELSE CURRENT_TIMESTAMP END, ?, ?, ?)
        ON CONFLICT(conversation_id) DO UPDATE SET
            status = excluded.status, cart_json = excluded.cart_json, order_details_json = excluded.order_details_json,
            confirmed_order_json = excluded.confirmed_order_json, messages_json = excluded.messages_json,
            handoff_reason = excluded.handoff_reason,
            handoff_created_at = CASE WHEN excluded.handoff_reason IS NULL THEN NULL ELSE COALESCE(conversations.handoff_created_at, excluded.handoff_created_at) END,
            pending_messages_json = excluded.pending_messages_json, pending_until = excluded.pending_until,
            processing_batch_json = excluded.processing_batch_json
        """,
        (
            conversation_state.conversation_id, conversation_state.status.value,
            _to_json(_cart_to_data(conversation_state.cart)), _to_json(_order_details_to_data(conversation_state.order_details)),
            _to_json(_order_to_data(conversation_state.confirmed_order)) if conversation_state.confirmed_order is not None else None,
            _to_json([_message_to_data(message) for message in conversation_state.messages]),
            _handoff_reason_to_value(conversation_state), _handoff_reason_to_value(conversation_state),
            _to_json([_pending_message_to_data(message) for message in conversation_state.pending_messages]),
            conversation_state.pending_until.isoformat() if conversation_state.pending_until else None,
            _to_json(_pending_batch_to_data(conversation_state.processing_batch)) if conversation_state.processing_batch else None,
        ),
    )


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
    if not isinstance(raw_items, list) or not all(isinstance(item, dict) for item in raw_items):
        raise ValueError("Conversation cart items must be a list.")
    return Cart(
        items=tuple(
            CartItem(product=_product_from_data(item["product"]), quantity=item["quantity"])
            for item in raw_items
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
        "presentation": product.presentation,
        "portions_or_units": product.portions_or_units,
        "description": product.description,
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
        presentation=data.get("presentation", ""),
        portions_or_units=data.get("portions_or_units", ""),
        description=data.get("description", ""),
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
    if not isinstance(raw_items, list) or not all(isinstance(item, dict) for item in raw_items):
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
    role = data["role"]
    content = data["content"]
    if role not in {"user", "assistant"} or not isinstance(content, str):
        raise ValueError("Conversation messages must have a supported role and text content.")
    return ConversationMessage(role=role, content=content)


def _pending_message_to_data(message: PendingMessage) -> dict[str, str]:
    return {"id": message.id, "content": message.content, "received_at": message.received_at.isoformat()}


def _pending_message_from_data(data: Mapping[str, Any]) -> PendingMessage:
    identifier, content, received_at = data["id"], data["content"], data["received_at"]
    if not isinstance(identifier, str) or not isinstance(content, str) or not isinstance(received_at, str):
        raise ValueError("Pending messages require an id, content, and timestamp.")
    return PendingMessage(id=identifier, content=content, received_at=datetime.fromisoformat(received_at))


def _pending_batch_to_data(batch: PendingMessageBatch) -> dict[str, object]:
    return {"id": batch.id, "messages": [_pending_message_to_data(message) for message in batch.messages]}


def _pending_batch_from_data(data: Mapping[str, Any]) -> PendingMessageBatch:
    identifier, messages = data["id"], data["messages"]
    if not isinstance(identifier, str) or not isinstance(messages, list) or not all(isinstance(item, dict) for item in messages):
        raise ValueError("Pending message batches require an id and messages.")
    return PendingMessageBatch(id=identifier, messages=tuple(_pending_message_from_data(item) for item in messages))


def _validate_loaded_state(state: ConversationState) -> None:
    """Reject impossible lifecycle data instead of letting later saves discard it."""

    if state.status is ConversationStatus.HUMAN_HANDOFF and state.handoff_reason is None:
        raise ValueError("Human handoff state is missing its reason.")
    if state.status is not ConversationStatus.HUMAN_HANDOFF and state.handoff_reason is not None:
        raise ValueError("Only human handoff state may include a reason.")
    if state.pending_until is not None and not state.pending_messages:
        raise ValueError("Only pending messages may have a debounce deadline.")
    if state.processing_batch is not None and state.pending_until is not None and not state.pending_messages:
        raise ValueError("A claimed batch cannot have a deadline without newer pending messages.")
