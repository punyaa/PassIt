"""Lender-declared availability windows and the date-picker view (B1).

Lives under /listings but is owned by B1: B3 owns the listing row, B1 owns its calendar.
"""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import Field
from sqlalchemy import delete, exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser
from app.core.db import DbSession
from app.models import Availability, Booking, Listing, inclusive_range, range_bounds
from app.schemas import ApiModel, DateWindow

router = APIRouter(prefix="/listings", tags=["bookings"])

BLOCKING_STATES = ("confirmed", "handed_over")


class AvailabilityResponse(ApiModel):
    listing_id: UUID
    from_date: date
    to_date: date
    available: bool = Field(description="True when the whole range can be booked.")
    windows: list[DateWindow] = Field(description="Lender-declared open windows.")
    booked: list[DateWindow] = Field(description="Booked ranges overlapping the query.")


class AvailabilityUpdate(ApiModel):
    windows: list[DateWindow] = Field(min_length=1, max_length=20)


async def _availability(
    db: AsyncSession, listing_id: UUID, start: date, end: date
) -> AvailabilityResponse:
    requested = inclusive_range(start, end)
    windows = await db.scalars(
        select(Availability.period)
        .where(Availability.listing_id == listing_id)
        .order_by(Availability.period)
    )
    booked = await db.scalars(
        select(Booking.period)
        .where(
            Booking.listing_id == listing_id,
            Booking.state.in_(BLOCKING_STATES),
            Booking.period.overlaps(requested),
        )
        .order_by(Booking.period)
    )
    window_list = [DateWindow(start_date=s, end_date=e) for s, e in map(range_bounds, windows)]
    booked_list = [DateWindow(start_date=s, end_date=e) for s, e in map(range_bounds, booked)]
    inside_window = any(w.start_date <= start and end <= w.end_date for w in window_list)
    return AvailabilityResponse(
        listing_id=listing_id,
        from_date=start,
        to_date=end,
        available=inside_window and not booked_list,
        windows=window_list,
        booked=booked_list,
    )


@router.get(
    "/{listing_id}/availability",
    response_model=AvailabilityResponse,
    operation_id="getListingAvailability",
)
async def get_listing_availability(
    listing_id: UUID,
    db: DbSession,
    from_date: Annotated[date, Query(alias="from")],
    to_date: Annotated[date, Query(alias="to")],
) -> AvailabilityResponse:
    """Advisory view for the date picker. The booking insert re-checks atomically."""
    if to_date < from_date:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "`to` must not be before `from`")
    listing_exists = await db.scalar(select(exists().where(Listing.id == listing_id)))
    if not listing_exists:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Listing not found")
    return await _availability(db, listing_id, from_date, to_date)


@router.put(
    "/{listing_id}/availability",
    response_model=AvailabilityResponse,
    operation_id="setListingAvailability",
)
async def set_listing_availability(
    listing_id: UUID, request: AvailabilityUpdate, user: CurrentUser, db: DbSession
) -> AvailabilityResponse:
    """Replace the listing's open windows. Existing bookings are unaffected."""
    listing = await db.get(Listing, listing_id)
    if listing is None or listing.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Listing not found")
    await db.execute(delete(Availability).where(Availability.listing_id == listing_id))
    db.add_all(
        Availability(listing_id=listing_id, period=inclusive_range(w.start_date, w.end_date))
        for w in request.windows
    )
    await db.commit()
    start = min(w.start_date for w in request.windows)
    end = max(w.end_date for w in request.windows)
    return await _availability(db, listing_id, start, end)
