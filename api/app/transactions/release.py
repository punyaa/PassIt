"""Scheduled fee release. Safe to run any number of times for the same booking."""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.core.db import get_sessionmaker
from app.integrations.notifications import publish_event
from app.models import Booking, LedgerEntry, Listing
from app.notifications.events import build_booking_event
from app.transactions import service

logger = logging.getLogger(__name__)

RELEASABLE_STATES = ("handed_over", "returned", "settled")


async def handle_release(booking_id: UUID | str, now: datetime | None = None) -> dict[str, Any]:
    """Release the rental fee to the lender once the hold period has passed.

    EventBridge may deliver more than once and the local sweep may race it; the row lock
    plus the "already released" check make every extra call a no-op.

    When a fee is released the result also carries the `fee.released` event. The caller
    delivers it: the Lambda's destination does so for the scheduled path (the function has
    no route to SNS), and `release_due_fees` publishes it for the sweep.
    """
    booking_id = UUID(str(booking_id))
    now = now or datetime.now(UTC)
    event: dict[str, Any] | None = None
    async with get_sessionmaker()() as db, db.begin():
        booking = await db.get(Booking, booking_id, with_for_update=True)
        if booking is None:
            status = "not_found"
        elif await service.fee_released(db, booking_id):
            status = "already_released"
        elif booking.state == "disputed":
            status = "held_for_dispute"
        elif booking.state not in RELEASABLE_STATES:
            status = f"not_releasable_in_{booking.state}"
        elif booking.fee_release_at is None or booking.fee_release_at > now:
            status = "not_due"
        else:
            await service.release_fee(db, booking)
            status = "released"
            listing = await db.get(Listing, booking.listing_id)
            event = await build_booking_event(db, "fee.released", booking, listing)
    logger.info("fee release %s: %s", booking_id, status)
    result: dict[str, Any] = {"booking_id": str(booking_id), "status": status}
    if event is not None:
        result["event"] = event
    return result


async def release_due_fees(now: datetime | None = None) -> list[dict[str, Any]]:
    """Sweep every booking whose hold period has ended and whose fee is still held."""
    now = now or datetime.now(UTC)
    already_released = select(LedgerEntry.booking_id).where(LedgerEntry.entry_type == "release_fee")
    async with get_sessionmaker()() as db:
        due = await db.scalars(
            select(Booking.id).where(
                Booking.fee_release_at <= now,
                Booking.state.in_(RELEASABLE_STATES),
                Booking.id.not_in(already_released),
            )
        )
        booking_ids = list(due)
    results = [await handle_release(booking_id, now) for booking_id in booking_ids]
    for result in results:
        if event := result.pop("event", None):
            await asyncio.to_thread(publish_event, event)
    return results


async def run_local_sweep(interval_seconds: int) -> None:
    """Background loop used when PASSIT_SCHEDULER_BACKEND=local."""
    while True:
        await asyncio.sleep(interval_seconds)
        try:
            await release_due_fees()
        except Exception:  # keep the loop alive; the next tick retries
            logger.exception("local fee-release sweep failed")
