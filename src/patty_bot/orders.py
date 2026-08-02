from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Literal

from patty_bot.cart import Cart
from patty_bot.config import DELIVERY_FEE, PICKUP_STORES


FulfillmentType = Literal["delivery", "pickup"]
# The requested production date must leave the business two full days of lead time.
MINIMUM_ADVANCE_DAYS = 2
# A confirmed local order still requires payment and operational review.
ORDER_STATUS_PENDING = "Pendiente de pago y revision"


@dataclass(frozen=True)
class OrderDetails:
    customer_name: str = ""
    customer_phone: str = ""
    fulfillment_type: FulfillmentType = "delivery"
    requested_date: date | None = None
    delivery_address: str = ""
    pickup_store: str = ""


@dataclass(frozen=True)
class OrderValidationResult:
    missing_fields: tuple[str, ...]
    invalid_fields: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return not self.missing_fields and not self.invalid_fields


@dataclass(frozen=True)
class OrderItem:
    """An immutable product snapshot captured when an order is confirmed."""

    product_id: str
    product_name: str
    unit_price: Decimal
    quantity: int
    line_subtotal: Decimal

    def __post_init__(self) -> None:
        if not self.product_id.strip():
            raise ValueError("Order item product id cannot be empty.")
        if not self.product_name.strip():
            raise ValueError("Order item product name cannot be empty.")
        if self.unit_price < Decimal("0"):
            raise ValueError("Order item unit price cannot be negative.")
        if type(self.quantity) is not int or self.quantity <= 0:
            raise ValueError("Order item quantity must be an integer greater than zero.")
        if self.line_subtotal != self.unit_price * self.quantity:
            raise ValueError("Order item subtotal must match unit price multiplied by quantity.")


@dataclass(frozen=True)
class Order:
    """The immutable aggregate persisted after a valid cart is confirmed."""

    details: OrderDetails
    items: tuple[OrderItem, ...]
    subtotal: Decimal
    delivery_fee: Decimal
    total: Decimal
    status: str
    created_at: datetime
    id: int | None = None

    def __post_init__(self) -> None:
        if self.id is not None and (type(self.id) is not int or self.id <= 0):
            raise ValueError("Order id must be a positive integer when provided.")
        if not self.items:
            raise ValueError("Order must contain at least one item.")
        if self.subtotal != sum((item.line_subtotal for item in self.items), Decimal("0")):
            raise ValueError("Order subtotal must match its item subtotals.")
        if self.delivery_fee < Decimal("0"):
            raise ValueError("Order delivery fee cannot be negative.")
        if self.total != self.subtotal + self.delivery_fee:
            raise ValueError("Order total must match subtotal plus delivery fee.")
        if not self.status.strip():
            raise ValueError("Order status cannot be empty.")


def validate_order_details(
    details: OrderDetails,
    reference_date: date | None = None,
) -> OrderValidationResult:
    # reference_date makes date-dependent rules deterministic in tests and tool calls.
    today = reference_date or date.today()
    missing_fields: list[str] = []
    invalid_fields: list[str] = []

    if not details.customer_name.strip():
        missing_fields.append("customer_name")
    if not details.customer_phone.strip():
        missing_fields.append("customer_phone")

    # Each fulfillment mode requires a different location field.
    if details.fulfillment_type == "delivery":
        if not details.delivery_address.strip():
            missing_fields.append("delivery_address")
    elif details.fulfillment_type == "pickup":
        if not details.pickup_store.strip():
            missing_fields.append("pickup_store")
        elif details.pickup_store not in PICKUP_STORES:
            invalid_fields.append("pickup_store")
    else:
        invalid_fields.append("fulfillment_type")

    if details.requested_date is None:
        missing_fields.append("requested_date")
    elif details.requested_date < minimum_requested_date(today):
        invalid_fields.append("requested_date")

    return OrderValidationResult(
        missing_fields=tuple(missing_fields),
        invalid_fields=tuple(invalid_fields),
    )


def minimum_requested_date(reference_date: date | None = None) -> date:
    today = reference_date or date.today()
    return today + timedelta(days=MINIMUM_ADVANCE_DAYS)


def delivery_fee_for_order(details: OrderDetails) -> Decimal:
    # Pickup has no delivery charge even though a bare Cart exposes the default fee for the legacy UI.
    if details.fulfillment_type == "delivery":
        return Decimal(str(DELIVERY_FEE))
    return Decimal("0")


def total_for_order(cart: Cart, details: OrderDetails) -> Decimal:
    return cart.subtotal + delivery_fee_for_order(details)


def create_confirmed_order(
    cart: Cart,
    details: OrderDetails,
    reference_date: date | None = None,
    created_at: datetime | None = None,
) -> Order:
    """Create the immutable order snapshot that can be safely persisted."""

    if cart.is_empty:
        raise ValueError("Cannot confirm an empty cart.")

    validation = validate_order_details(details, reference_date=reference_date)
    if not validation.is_valid:
        problems = (*validation.missing_fields, *validation.invalid_fields)
        raise ValueError(f"Cannot confirm order with invalid details: {', '.join(problems)}")

    # Copy product values now so later catalog changes cannot alter this confirmed order.
    items = tuple(
        OrderItem(
            product_id=item.product.id,
            product_name=item.product.name,
            unit_price=item.product.price,
            quantity=item.quantity,
            line_subtotal=item.line_subtotal,
        )
        for item in cart.items
    )
    delivery_fee = delivery_fee_for_order(details)
    return Order(
        details=details,
        items=items,
        subtotal=cart.subtotal,
        delivery_fee=delivery_fee,
        total=cart.subtotal + delivery_fee,
        status=ORDER_STATUS_PENDING,
        created_at=created_at or datetime.now(),
    )
