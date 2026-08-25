"""Tests for deterministic customer date interpretation in Patty's Lima timezone."""

from datetime import date, datetime, timezone

import pytest

from patty_bot.domain.natural_dates import NaturalDateError, interpret_requested_date, lima_today


REFERENCE_DATE = date(2026, 11, 20)


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("mañana", date(2026, 11, 21)),
        ("pasado mañana", date(2026, 11, 22)),
        ("el próximo lunes", date(2026, 11, 23)),
        ("este viernes", date(2026, 11, 20)),
    ],
)
def test_interpret_requested_date_resolves_relative_dates(expression: str, expected: date) -> None:
    interpretation = interpret_requested_date(expression, reference_date=REFERENCE_DATE)

    assert interpretation.value == expected
    assert interpretation.inferred is True


def test_interpret_requested_date_uses_the_next_year_for_a_passed_day_and_month() -> None:
    interpretation = interpret_requested_date("15 de febrero", reference_date=REFERENCE_DATE)

    assert interpretation.value == date(2027, 2, 15)
    assert interpretation.inferred is True


def test_interpret_requested_date_keeps_explicit_year() -> None:
    interpretation = interpret_requested_date("15 de febrero de 2028", reference_date=REFERENCE_DATE)

    assert interpretation.value == date(2028, 2, 15)
    assert interpretation.inferred is False


def test_interpret_requested_date_asks_for_day_when_only_month_is_given() -> None:
    with pytest.raises(NaturalDateError, match="needs a day"):
        interpret_requested_date("en febrero", reference_date=REFERENCE_DATE)


def test_lima_today_uses_lima_date_not_the_server_utc_date() -> None:
    utc_time = datetime(2026, 11, 21, 3, 30, tzinfo=timezone.utc)

    assert lima_today(utc_time) == date(2026, 11, 20)
