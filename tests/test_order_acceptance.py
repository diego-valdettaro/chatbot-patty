from datetime import date
from decimal import Decimal

from patty_bot.cart import Cart, CartItem
from patty_bot.catalog import Product
from patty_bot.orders import OrderDetails, delivery_fee_for_order, total_for_order, validate_order_details


REFERENCE_DATE = date(2026, 7, 22)
VALID_REQUESTED_DATE = date(2026, 7, 24)


def make_cart() -> Cart:
    product = Product(
        id="brownie-chocolate-belga",
        name="Brownie de chocolate belga",
        aliases=(),
        category="Brownies",
        price=Decimal("8.00"),
        active=True,
    )
    return Cart(items=(CartItem(product=product, quantity=2),))


def test_order_acceptance_delivery_requires_address():
    details = OrderDetails(
        customer_name="Diego",
        customer_phone="999999999",
        fulfillment_type="delivery",
        requested_date=VALID_REQUESTED_DATE,
    )

    result = validate_order_details(details, reference_date=REFERENCE_DATE)

    assert result.is_valid is False
    assert result.missing_fields == ("delivery_address",)


def test_order_acceptance_pickup_requires_store():
    details = OrderDetails(
        customer_name="Diego",
        customer_phone="999999999",
        fulfillment_type="pickup",
        requested_date=VALID_REQUESTED_DATE,
    )

    result = validate_order_details(details, reference_date=REFERENCE_DATE)

    assert result.is_valid is False
    assert result.missing_fields == ("pickup_store",)


def test_order_acceptance_rejects_date_with_less_than_two_days():
    details = OrderDetails(
        customer_name="Diego",
        customer_phone="999999999",
        fulfillment_type="delivery",
        requested_date=date(2026, 7, 23),
        delivery_address="Av. Benavides 123",
    )

    result = validate_order_details(details, reference_date=REFERENCE_DATE)

    assert result.is_valid is False
    assert result.invalid_fields == ("requested_date",)


def test_order_acceptance_delivery_validates_and_adds_delivery_fee():
    details = OrderDetails(
        customer_name="Diego",
        customer_phone="999999999",
        fulfillment_type="delivery",
        requested_date=VALID_REQUESTED_DATE,
        delivery_address="Av. Benavides 123",
    )

    result = validate_order_details(details, reference_date=REFERENCE_DATE)

    assert result.is_valid is True
    assert delivery_fee_for_order(details) == Decimal("10")
    assert total_for_order(make_cart(), details) == Decimal("26.00")


def test_order_acceptance_pickup_validates_and_has_zero_delivery_fee():
    details = OrderDetails(
        customer_name="Diego",
        customer_phone="999999999",
        fulfillment_type="pickup",
        requested_date=VALID_REQUESTED_DATE,
        pickup_store="San Isidro",
    )

    result = validate_order_details(details, reference_date=REFERENCE_DATE)

    assert result.is_valid is True
    assert delivery_fee_for_order(details) == Decimal("0")
    assert total_for_order(make_cart(), details) == Decimal("16.00")
