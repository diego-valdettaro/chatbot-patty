from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Literal

from patty_bot.cart import Cart
from patty_bot.config import DELIVERY_FEE, PICKUP_STORES


FulfillmentType = Literal["delivery", "pickup"]
MINIMUM_ADVANCE_DAYS = 2


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


def validate_order_details(
    details: OrderDetails,
    reference_date: date | None = None,
) -> OrderValidationResult:
    today = reference_date or date.today()
    missing_fields: list[str] = []
    invalid_fields: list[str] = []

    if not details.customer_name.strip():
        missing_fields.append("customer_name")
    if not details.customer_phone.strip():
        missing_fields.append("customer_phone")

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
    if details.fulfillment_type == "delivery":
        return Decimal(str(DELIVERY_FEE))
    return Decimal("0")


def total_for_order(cart: Cart, details: OrderDetails) -> Decimal:
    return cart.subtotal + delivery_fee_for_order(details)
