from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.bookings.pricing import price_for
from app.bookings.state_machine import available_actions, require_action
from app.models import inclusive_range, range_bounds

LISTING = SimpleNamespace(price_day=Decimal("12.00"), price_week=Decimal("50.00"), price_month=None)


@pytest.mark.parametrize(
    ("duration", "start", "end", "fee"),
    [
        ("day", date(2026, 11, 1), date(2026, 11, 1), "12.00"),
        ("day", date(2026, 11, 1), date(2026, 11, 3), "36.00"),
        ("week", date(2026, 11, 1), date(2026, 11, 7), "50.00"),
        ("week", date(2026, 11, 1), date(2026, 11, 8), "100.00"),
    ],
)
def test_price_for_inclusive_dates(duration, start, end, fee) -> None:
    assert price_for(LISTING, duration, start, end) == Decimal(fee)


def test_price_for_unoffered_duration() -> None:
    with pytest.raises(HTTPException) as error:
        price_for(LISTING, "month", date(2026, 11, 1), date(2026, 11, 30))
    assert error.value.status_code == 400


def test_range_round_trip_is_inclusive() -> None:
    assert range_bounds(inclusive_range(date(2026, 11, 1), date(2026, 11, 7))) == (
        date(2026, 11, 1),
        date(2026, 11, 7),
    )


def test_actions_per_role() -> None:
    assert available_actions("confirmed", "borrower", False) == ["handover", "cancel"]
    assert available_actions("returned", "lender", False) == ["settle", "report_damage", "review"]
    assert available_actions("settled", "borrower", True) == []
    with pytest.raises(HTTPException) as wrong_party:
        require_action("settle", "returned", "borrower")
    assert wrong_party.value.status_code == 403
    with pytest.raises(HTTPException) as wrong_state:
        require_action("return", "confirmed", "lender")
    assert wrong_state.value.status_code == 409
