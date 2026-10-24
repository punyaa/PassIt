from datetime import date
from decimal import Decimal
from math import ceil

from fastapi import HTTPException, status

from app.models import Listing

UNIT_DAYS = {"day": 1, "week": 7, "month": 30}
ADJECTIVE = {"day": "daily", "week": "weekly", "month": "monthly"}


def rental_days(start: date, end: date) -> int:
    """Both dates are inclusive: a same-day rental is one day."""
    return (end - start).days + 1


def price_for(listing: Listing, duration_type: str, start: date, end: date) -> Decimal:
    """Charge whole units of the chosen duration, rounding partial units up."""
    rate = {"day": listing.price_day, "week": listing.price_week, "month": listing.price_month}[
        duration_type
    ]
    if rate is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"This listing has no {ADJECTIVE[duration_type]} price"
        )
    units = ceil(rental_days(start, end) / UNIT_DAYS[duration_type])
    return (rate * units).quantize(Decimal("0.01"))
