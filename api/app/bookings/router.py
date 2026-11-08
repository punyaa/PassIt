import asyncio
import logging
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from pydantic import Field
from sqlalchemy import exists, or_, select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser
from app.bookings.pricing import price_for, rental_days
from app.bookings.state_machine import Role, available_actions, require_action
from app.core.config import get_settings
from app.core.db import DbSession
from app.integrations.notifications import publish_event
from app.integrations.scheduler import get_scheduler
from app.integrations.storage import get_storage
from app.media.service import attach_media
from app.memberships.plans import deposit_for, fee_hold_minutes_for
from app.memberships.service import plan_for
from app.models import Availability, Checklist, Listing, Media, Review, User, inclusive_range
from app.models import Booking as BookingRow
from app.notifications.events import Actor, EventType, build_booking_event
from app.payments import service as payment_service
from app.payments.gateway import PaymentGatewayError
from app.schemas import ApiModel
from app.transactions import service as ledger_service

logger = logging.getLogger(__name__)

DEADLOCK_DETECTED = "40P01"  # PostgreSQL SQLSTATE for an aborted deadlock victim

router = APIRouter(prefix="/bookings", tags=["bookings"])

BookingState = Literal[
    "requested", "confirmed", "handed_over", "returned", "settled", "cancelled", "disputed"
]
DurationType = Literal["day", "week", "month"]
Action = Literal["handover", "cancel", "return", "settle", "report_damage", "review"]


class BookingCreate(ApiModel):
    listing_id: UUID
    start_date: date
    end_date: date
    duration_type: DurationType
    payment_method_token: Literal[
        "pm_mock_success",
        "pm_mock_declined",
        "pm_mock_insufficient_funds",
        "pm_mock_expired",
        "pm_mock_processing_error",
    ] = "pm_mock_success"


class Booking(ApiModel):
    id: UUID
    listing_id: UUID
    listing_title: str
    lender_id: UUID
    borrower_id: UUID
    start_date: date
    end_date: date
    duration_type: DurationType
    fee: Decimal
    deposit: Decimal
    state: BookingState
    created_at: datetime
    handed_over_at: datetime | None = None
    returned_at: datetime | None = None
    fee_release_at: datetime | None = None
    fee_released: bool = False
    settled_at: datetime | None = None
    cancelled_at: datetime | None = None
    damage_severity: Literal["none", "minor", "moderate", "severe", "total"] | None = None
    viewer_role: Role
    available_actions: list[Action]


class ChecklistItem(ApiModel):
    label: str = Field(min_length=1, max_length=200)
    checked: bool


class ChecklistSubmission(ApiModel):
    items: list[ChecklistItem] = Field(min_length=1, max_length=30)
    media_keys: list[str] = Field(
        min_length=1,
        max_length=10,
        description="Condition photos uploaded via POST /media/presign for this stage.",
    )


class DamageSubmission(ApiModel):
    severity: Literal["minor", "moderate", "severe", "total"]
    notes: str = Field(min_length=1, max_length=2000)


class ChecklistRecord(ApiModel):
    stage: Literal["handover", "return"]
    items: list[ChecklistItem]
    signed_by: UUID | None
    signed_at: datetime | None
    media_urls: list[str]


# --- helpers -------------------------------------------------------------------------


async def _load_for_party(
    db: AsyncSession, booking_id: UUID, user_id: UUID, *, lock: bool = False
) -> tuple[BookingRow, Listing, Role]:
    """Load a booking the caller takes part in. `lock` serialises lifecycle changes."""
    query = select(BookingRow).where(BookingRow.id == booking_id)
    if lock:
        query = query.with_for_update()
    booking = await db.scalar(query)
    listing = booking and await db.get(Listing, booking.listing_id)
    if booking is None or user_id not in (booking.borrower_id, listing.owner_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found")
    return booking, listing, "borrower" if user_id == booking.borrower_id else "lender"


async def _to_response(
    db: AsyncSession, booking: BookingRow, listing: Listing, viewer_id: UUID
) -> Booking:
    role: Role = "borrower" if viewer_id == booking.borrower_id else "lender"
    released = await ledger_service.fee_released(db, booking.id)
    reviewed = bool(
        await db.scalar(
            select(exists().where(Review.booking_id == booking.id, Review.author_id == viewer_id))
        )
    )
    return Booking(
        id=booking.id,
        listing_id=booking.listing_id,
        listing_title=listing.title,
        lender_id=listing.owner_id,
        borrower_id=booking.borrower_id,
        start_date=booking.start_date,
        end_date=booking.end_date,
        duration_type=booking.duration_type,
        fee=booking.fee,
        deposit=booking.deposit,
        state=booking.state,
        created_at=booking.created_at,
        handed_over_at=booking.handed_over_at,
        returned_at=booking.returned_at,
        fee_release_at=booking.fee_release_at,
        fee_released=released,
        settled_at=booking.settled_at,
        cancelled_at=booking.cancelled_at,
        damage_severity=booking.damage_severity,
        viewer_role=role,
        available_actions=available_actions(booking.state, role, reviewed),
    )


async def _announce(
    background: BackgroundTasks,
    db: AsyncSession,
    event_type: EventType,
    booking: BookingRow,
    listing: Listing,
    actor: Actor,
) -> None:
    """Queue an event to go out once the response is sent. The change already committed, so
    a failure to describe or publish it is logged and never fails the request."""
    try:
        background.add_task(
            publish_event, await build_booking_event(db, event_type, booking, listing, actor)
        )
    except Exception:
        logger.exception("could not build %s for %s", event_type, booking.id)


async def _within_availability(db: AsyncSession, listing_id: UUID, start: date, end: date) -> bool:
    return bool(
        await db.scalar(
            select(
                exists().where(
                    Availability.listing_id == listing_id,
                    Availability.period.contains(inclusive_range(start, end)),
                )
            )
        )
    )


def _constraint_name(error: IntegrityError) -> str | None:
    diag = getattr(error.orig, "diag", None)
    return getattr(diag, "constraint_name", None)


async def _record_checklist(
    db: AsyncSession, booking: BookingRow, stage: str, submission: ChecklistSubmission, user: User
) -> None:
    db.add(
        Checklist(
            booking_id=booking.id,
            stage=stage,
            items=[item.model_dump() for item in submission.items],
            signed_by=user.id,
            signed_at=datetime.now(UTC),
        )
    )
    await attach_media(db, submission.media_keys, stage, user.id, booking_id=booking.id)


# --- routes --------------------------------------------------------------------------


@router.post(
    "",
    response_model=Booking,
    status_code=status.HTTP_201_CREATED,
    operation_id="createBooking",
    responses={
        402: {"description": "Mock payment failed"},
        409: {"description": "Dates already booked or outside availability"},
    },
)
async def create_booking(
    request: BookingCreate, user: CurrentUser, db: DbSession, background: BackgroundTasks
) -> Booking:
    """Book dates instantly. The exclusion constraint `no_overlap` is the only guard against
    double-booking: there is no check-then-insert, so concurrent requests for the same dates
    produce exactly one 201 and 409 for the rest."""
    start, end = request.start_date, request.end_date
    if end < start:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "end_date must not be before start_date")
    if start < date.today():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "start_date is in the past")
    if rental_days(start, end) > get_settings().max_rental_days:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Rental period is too long")

    listing = await db.get(Listing, request.listing_id)
    if listing is None or listing.status != "active":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Listing not available")
    if listing.owner_id == user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot borrow your own item")
    if not await _within_availability(db, listing.id, start, end):
        raise HTTPException(status.HTTP_409_CONFLICT, "Dates outside availability")

    booking = BookingRow(
        listing_id=listing.id,
        borrower_id=user.id,
        period=inclusive_range(start, end),
        duration_type=request.duration_type,
        fee=price_for(listing, request.duration_type, start, end),
        deposit=deposit_for(await plan_for(db, user.id), listing.deposit),
        state="confirmed",
    )
    db.add(booking)
    try:
        await db.flush()  # the exclusion constraint fires here
        await payment_service.collect_booking_payment(db, booking, request.payment_method_token)
        await ledger_service.hold_funds(db, booking)  # same transaction as the booking
        await db.commit()
    except PaymentGatewayError as error:
        await db.rollback()
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, detail=error.detail()) from error
    except IntegrityError as error:
        await db.rollback()
        if _constraint_name(error) == "no_overlap":
            raise HTTPException(
                status.HTTP_409_CONFLICT, "Those dates are already booked"
            ) from error
        if _constraint_name(error) == "bookings_listing_id_fkey":
            # The lender deleted the listing while this request was in flight.
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Listing not available") from error
        raise
    except OperationalError as error:
        await db.rollback()
        # Two requests for overlapping but different ranges can wait on each other while
        # PostgreSQL checks the exclusion constraint. It aborts exactly one with a deadlock
        # error and the other keeps the dates, so the aborted request lost them like any
        # other conflict and must not surface as a 500.
        if getattr(error.orig, "sqlstate", None) == DEADLOCK_DETECTED:
            raise HTTPException(
                status.HTTP_409_CONFLICT, "Those dates are already booked"
            ) from error
        raise
    await db.refresh(booking)
    await _announce(background, db, "booking.confirmed", booking, listing, "borrower")
    return await _to_response(db, booking, listing, user.id)


@router.get("", response_model=list[Booking], operation_id="listBookings")
async def list_bookings(
    user: CurrentUser,
    db: DbSession,
    role: Literal["borrower", "lender", "all"] = "all",
    state: BookingState | None = None,
    limit: int = Query(50, ge=1, le=100),
) -> list[Booking]:
    query = select(BookingRow, Listing).join(Listing, Listing.id == BookingRow.listing_id)
    as_borrower = BookingRow.borrower_id == user.id
    as_lender = Listing.owner_id == user.id
    query = query.where(
        {"borrower": as_borrower, "lender": as_lender, "all": or_(as_borrower, as_lender)}[role]
    )
    if state:
        query = query.where(BookingRow.state == state)
    rows = await db.execute(query.order_by(BookingRow.created_at.desc()).limit(limit))
    return [await _to_response(db, booking, listing, user.id) for booking, listing in rows]


@router.get("/{booking_id}", response_model=Booking, operation_id="getBooking")
async def get_booking(booking_id: UUID, user: CurrentUser, db: DbSession) -> Booking:
    booking, listing, _ = await _load_for_party(db, booking_id, user.id)
    return await _to_response(db, booking, listing, user.id)


@router.post("/{booking_id}/handover", response_model=Booking, operation_id="handoverBooking")
async def handover_booking(
    booking_id: UUID,
    submission: ChecklistSubmission,
    user: CurrentUser,
    db: DbSession,
    background: BackgroundTasks,
) -> Booking:
    """Record the handover checklist and condition photos, and start the fee hold timer."""
    booking, listing, role = await _load_for_party(db, booking_id, user.id, lock=True)
    require_action("handover", booking.state, role)
    now = datetime.now(UTC)
    await _record_checklist(db, booking, "handover", submission, user)
    booking.state = "handed_over"
    booking.handed_over_at = now
    # Faster payouts are a lender perk: the hold follows the lender's plan.
    hold = fee_hold_minutes_for(
        await plan_for(db, listing.owner_id), get_settings().fee_hold_minutes
    )
    booking.fee_release_at = now + timedelta(minutes=hold)
    await db.commit()
    try:
        # After commit: a rolled-back handover must never leave a live schedule behind.
        await asyncio.to_thread(
            get_scheduler().schedule_fee_release, booking.id, booking.fee_release_at
        )
    except Exception:  # the release sweep is the safety net
        logger.exception("could not schedule fee release for %s", booking.id)
    await _announce(background, db, "booking.handed_over", booking, listing, role)
    return await _to_response(db, booking, listing, user.id)


@router.post("/{booking_id}/return", response_model=Booking, operation_id="returnBooking")
async def return_booking(
    booking_id: UUID,
    submission: ChecklistSubmission,
    user: CurrentUser,
    db: DbSession,
    background: BackgroundTasks,
) -> Booking:
    """Record the return checklist and photos. The lender then settles the deposit."""
    booking, listing, role = await _load_for_party(db, booking_id, user.id, lock=True)
    require_action("return", booking.state, role)
    await _record_checklist(db, booking, "return", submission, user)
    booking.state = "returned"
    booking.returned_at = datetime.now(UTC)
    await db.commit()
    await _announce(background, db, "booking.returned", booking, listing, role)
    return await _to_response(db, booking, listing, user.id)


@router.post("/{booking_id}/cancel", response_model=Booking, operation_id="cancelBooking")
async def cancel_booking(
    booking_id: UUID, user: CurrentUser, db: DbSession, background: BackgroundTasks
) -> Booking:
    """Cancel before handover. Both holds are refunded and the dates are freed."""
    booking, listing, role = await _load_for_party(db, booking_id, user.id, lock=True)
    require_action("cancel", booking.state, role)
    await payment_service.refund_cancelled_booking(db, booking)
    await ledger_service.reverse_holds(db, booking)
    booking.state = "cancelled"
    booking.cancelled_at = datetime.now(UTC)
    await db.commit()
    await _announce(background, db, "booking.cancelled", booking, listing, role)
    return await _to_response(db, booking, listing, user.id)


async def _settle(
    db: AsyncSession,
    background: BackgroundTasks,
    booking_id: UUID,
    user: User,
    action: str,
    severity: str,
    notes: str | None,
) -> Booking:
    booking, listing, role = await _load_for_party(db, booking_id, user.id, lock=True)
    require_action(action, booking.state, role)
    await payment_service.settle_deposit(db, booking, listing.owner_id, severity)
    await ledger_service.settle_deposit(db, booking, severity)
    booking.damage_severity = severity
    booking.damage_notes = notes
    booking.state = "settled"
    booking.settled_at = datetime.now(UTC)
    await db.commit()
    await _announce(background, db, "booking.settled", booking, listing, role)
    return await _to_response(db, booking, listing, user.id)


@router.post("/{booking_id}/settle", response_model=Booking, operation_id="settleBooking")
async def settle_booking(
    booking_id: UUID, user: CurrentUser, db: DbSession, background: BackgroundTasks
) -> Booking:
    """Lender confirms the item came back fine: the full deposit is refunded."""
    return await _settle(db, background, booking_id, user, "settle", "none", None)


@router.post("/{booking_id}/damage", response_model=Booking, operation_id="reportBookingDamage")
async def report_booking_damage(
    booking_id: UUID,
    submission: DamageSubmission,
    user: CurrentUser,
    db: DbSession,
    background: BackgroundTasks,
) -> Booking:
    """Lender reports damage after comparing handover and return evidence. The deposit is
    split by fixed tier: minor 20%, moderate 40%, severe 70%, total 100% to the lender.

    Prototype simplification: the plan has an admin choose the tier; with no admin role
    yet, the lender's tier is applied directly."""
    return await _settle(
        db, background, booking_id, user, "report_damage", submission.severity, submission.notes
    )


@router.get(
    "/{booking_id}/checklists",
    response_model=list[ChecklistRecord],
    operation_id="getBookingChecklists",
)
async def get_booking_checklists(
    booking_id: UUID, user: CurrentUser, db: DbSession
) -> list[ChecklistRecord]:
    """Handover and return evidence side by side, for the damage comparison screen."""
    await _load_for_party(db, booking_id, user.id)
    checklists = await db.scalars(
        select(Checklist).where(Checklist.booking_id == booking_id).order_by(Checklist.signed_at)
    )
    media = await db.scalars(
        select(Media).where(Media.booking_id == booking_id).order_by(Media.created_at, Media.id)
    )
    storage = get_storage()
    urls: dict[str, list[str]] = {"handover": [], "return": []}
    for item in media:
        urls[item.stage].append(storage.view_url(item.s3_key))
    return [
        ChecklistRecord(
            stage=checklist.stage,
            items=checklist.items,
            signed_by=checklist.signed_by,
            signed_at=checklist.signed_at,
            media_urls=urls[checklist.stage],
        )
        for checklist in checklists
    ]
