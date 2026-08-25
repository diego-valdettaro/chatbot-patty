"""Deterministic interpretation of the Spanish dates accepted by Patty."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
import re
import unicodedata
from zoneinfo import ZoneInfo


LIMA_TIME_ZONE = ZoneInfo("America/Lima")

_MONTHS = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}
_WEEKDAYS = {
    "lunes": 0, "martes": 1, "miercoles": 2, "jueves": 3, "viernes": 4,
    "sabado": 5, "domingo": 6,
}


@dataclass(frozen=True)
class NaturalDateInterpretation:
    """A resolved date and whether Patty must communicate an inference."""

    value: date
    inferred: bool
    interpretation: str


class NaturalDateError(ValueError):
    """The supplied customer expression does not identify one calendar date."""


def lima_today(now: datetime | None = None) -> date:
    """Return Patty's business date, independently of the server time zone."""

    if now is None:
        return datetime.now(LIMA_TIME_ZONE).date()
    if now.tzinfo is None:
        raise ValueError("A supplied business clock must be timezone-aware.")
    return now.astimezone(LIMA_TIME_ZONE).date()


def interpret_requested_date(value: str, *, reference_date: date | None = None) -> NaturalDateInterpretation:
    """Resolve supported Spanish dates using Patty's Lima business clock."""

    raw_value = value.strip()
    if not raw_value:
        raise NaturalDateError("requested_date cannot be empty.")
    try:
        return NaturalDateInterpretation(date.fromisoformat(raw_value), False, "exact_date")
    except ValueError:
        pass

    normalized = _normalize(raw_value)
    today = reference_date or lima_today()
    relative_days = {"hoy": 0, "manana": 1, "pasado manana": 2}
    if normalized in relative_days:
        return NaturalDateInterpretation(
            today + timedelta(days=relative_days[normalized]), True, normalized.replace(" ", "_"),
        )

    weekday_match = re.fullmatch(
        r"(?:el )?(?:(este|proximo) )?(lunes|martes|miercoles|jueves|viernes|sabado|domingo)", normalized
    )
    if weekday_match:
        qualifier, weekday_name = weekday_match.groups()
        delta = (_WEEKDAYS[weekday_name] - today.weekday()) % 7
        if qualifier == "proximo" and delta == 0:
            delta = 7
        return NaturalDateInterpretation(today + timedelta(days=delta), True, "weekday")

    day_month_match = re.fullmatch(r"(?:el )?(\d{1,2})(?: de)? ([a-z]+)(?: de (\d{4}))?", normalized)
    if day_month_match:
        day_text, month_name, year_text = day_month_match.groups()
        month = _MONTHS.get(month_name)
        if month is None:
            raise NaturalDateError("requested_date contains an unsupported month.")
        day = int(day_text)
        if year_text:
            return _calendar_date(int(year_text), month, day, inferred=False, interpretation="exact_date")
        candidate = _calendar_date(today.year, month, day, inferred=True, interpretation="day_and_month")
        if candidate.value < today:
            candidate = _calendar_date(today.year + 1, month, day, inferred=True, interpretation="day_and_month")
        return candidate

    if re.fullmatch(r"(?:en )?[a-z]+", normalized) and normalized.removeprefix("en ") in _MONTHS:
        raise NaturalDateError("requested_date needs a day of the month.")
    raise NaturalDateError("requested_date must be an ISO date or a supported Spanish date expression.")


def _calendar_date(year: int, month: int, day: int, *, inferred: bool, interpretation: str) -> NaturalDateInterpretation:
    try:
        value = date(year, month, day)
    except ValueError as error:
        raise NaturalDateError("requested_date is not a valid calendar date.") from error
    return NaturalDateInterpretation(value, inferred, interpretation)


def _normalize(value: str) -> str:
    without_accents = "".join(
        character for character in unicodedata.normalize("NFD", value.lower()) if unicodedata.category(character) != "Mn"
    )
    return " ".join(without_accents.split())
