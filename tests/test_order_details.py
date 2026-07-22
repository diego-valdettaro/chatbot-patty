from datetime import date
from decimal import Decimal

from patty_bot.cart import Cart, CartItem
from patty_bot.catalog import Product
from patty_bot.orders import (
    OrderDetails,
    delivery_fee_for_order,
    minimum_requested_date,
    total_for_order,
    validate_order_details,
)


REFERENCE_DATE = date(2026, 7, 22)


def make_product() -> Product:
    return Product(
        id="brownie-chocolate-belga",
        name="Brownie de chocolate belga",
        aliases=(),
        category="Brownies",
        price=Decimal("8.00"),
        active=True,
    )


def valid_delivery_details() -> OrderDetails:
    return OrderDetails(
        customer_name="Diego",
        customer_phone="999999999",
        fulfillment_type="delivery",
        requested_date=date(2026, 7, 24),
        delivery_address="Av. Benavides 123",
    )


def test_order_details_keeps_customer_and_fulfillment_fields():
    details = valid_delivery_details()

    assert details.customer_name == "Diego"
    assert details.customer_phone == "999999999"
    assert details.fulfillment_type == "delivery"
    assert details.requested_date == date(2026, 7, 24)
    assert details.delivery_address == "Av. Benavides 123"


def test_validate_order_details_reports_missing_basic_fields():
    result = validate_order_details(OrderDetails(), reference_date=REFERENCE_DATE)

    assert result.is_valid is False
    assert result.missing_fields == (
        "customer_name",
        "customer_phone",
        "delivery_address",
        "requested_date",
    )
    assert result.invalid_fields == ()


def test_delivery_details_require_address():
    details = OrderDetails(
        customer_name="Diego",
        customer_phone="999999999",
        fulfillment_type="delivery",
        requested_date=date(2026, 7, 24),
    )

    result = validate_order_details(details, reference_date=REFERENCE_DATE)

    assert result.missing_fields == ("delivery_address",)
    assert result.invalid_fields == ()


def test_pickup_details_require_store():
    details = OrderDetails(
        customer_name="Diego",
        customer_phone="999999999",
        fulfillment_type="pickup",
        requested_date=date(2026, 7, 24),
    )

    result = validate_order_details(details, reference_date=REFERENCE_DATE)

    assert result.missing_fields == ("pickup_store",)
    assert result.invalid_fields == ()


def test_pickup_details_reject_unknown_store():
    details = OrderDetails(
        customer_name="Diego",
        customer_phone="999999999",
        fulfillment_type="pickup",
        requested_date=date(2026, 7, 24),
        pickup_store="Miraflores",
    )

    result = validate_order_details(details, reference_date=REFERENCE_DATE)

    assert result.missing_fields == ()
    assert result.invalid_fields == ("pickup_store",)


def test_requested_date_must_have_two_days_advance():
    details = OrderDetails(
        customer_name="Diego",
        customer_phone="999999999",
        fulfillment_type="delivery",
        requested_date=date(2026, 7, 23),
        delivery_address="Av. Benavides 123",
    )

    result = validate_order_details(details, reference_date=REFERENCE_DATE)

    assert result.missing_fields == ()
    assert result.invalid_fields == ("requested_date",)


def test_requested_date_with_two_days_advance_is_valid():
    result = validate_order_details(valid_delivery_details(), reference_date=REFERENCE_DATE)

    assert result.is_valid is True


def test_minimum_requested_date_uses_reference_date_plus_two_days():
    assert minimum_requested_date(REFERENCE_DATE) == date(2026, 7, 24)


def test_delivery_fee_depends_on_fulfillment_type():
    delivery = valid_delivery_details()
    pickup = OrderDetails(
        customer_name="Diego",
        customer_phone="999999999",
        fulfillment_type="pickup",
        requested_date=date(2026, 7, 24),
        pickup_store="Benavides",
    )

    assert delivery_fee_for_order(delivery) == Decimal("10")
    assert delivery_fee_for_order(pickup) == Decimal("0")


def test_total_for_order_uses_cart_subtotal_and_order_delivery_fee():
    cart = Cart(items=(CartItem(product=make_product(), quantity=2),))
    delivery = valid_delivery_details()
    pickup = OrderDetails(
        customer_name="Diego",
        customer_phone="999999999",
        fulfillment_type="pickup",
        requested_date=date(2026, 7, 24),
        pickup_store="Benavides",
    )

    assert total_for_order(cart, delivery) == Decimal("26.00")
    assert total_for_order(cart, pickup) == Decimal("16.00")
