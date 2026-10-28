"""Event documents describing what happened to a booking.

An event carries everything a consumer needs (names, emails, dates, money), so the mailer
Lambda never has to query the database. Events are plain JSON-ready dicts, version 1:

    event_id     unique id, so a consumer can spot a duplicate delivery
    version      1
    type         booking.confirmed | booking.handed_over | booking.returned |
                 booking.settled | booking.cancelled | fee.released
    occurred_at  ISO 8601, UTC
    actor        "borrower" | "lender" | "system"
    booking      id, listing_id, listing_title, start_date, end_date, duration_type, fee,
                 deposit, state, damage_severity, fee_release_at
    borrower     name, email
    lender       name, email

`booking.settled` also covers a damage report: damage_severity is then not "none".
infra/lambdas/mailer renders these, so keep the two in step.
"""

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Booking as BookingRow
from app.models import Listing as ListingRow
from app.models import User

EventType = Literal[
    "booking.confirmed",
    "booking.handed_over",
    "booking.returned",
    "booking.settled",
    "booking.cancelled",
    "fee.released",
]
Actor = Literal["borrower", "lender", "system"]
EVENT_VERSION = 1


def _person(user: User) -> dict[str, str]:
    return {"name": user.display_name, "email": user.email}


async def build_booking_event(
    db: AsyncSession,
    event_type: EventType,
    booking: BookingRow,
    listing: ListingRow,
    actor: Actor = "system",
) -> dict[str, Any]:
    borrower = await db.get(User, booking.borrower_id)
    lender = await db.get(User, listing.owner_id)
    return {
        "event_id": str(uuid4()),
        "version": EVENT_VERSION,
        "type": event_type,
        "occurred_at": datetime.now(UTC).isoformat(),
        "actor": actor,
        "booking": {
            "id": str(booking.id),
            "listing_id": str(listing.id),
            "listing_title": listing.title,
            "start_date": booking.start_date.isoformat(),
            "end_date": booking.end_date.isoformat(),
            "duration_type": booking.duration_type,
            "fee": str(booking.fee),
            "deposit": str(booking.deposit),
            "state": booking.state,
            "damage_severity": booking.damage_severity,
            "fee_release_at": booking.fee_release_at.isoformat()
            if booking.fee_release_at
            else None,
        },
        "borrower": _person(borrower),
        "lender": _person(lender),
    }
