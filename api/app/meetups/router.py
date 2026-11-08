"""Meetups: a borrower proposes when, where and for how much to meet the lender of a listing.

The two sides take turns. Whoever made the latest offer (`proposed_by`) waits; the other person
may accept it, counter with new terms, or decline. Making an offer counts as agreeing to it, so
one accept means both sides have agreed and the meeting is scheduled. The person who made the
latest offer may withdraw it, and either side may cancel a scheduled meeting before it happens.

Meetups only coordinate the two people: they never create a booking or move money.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import Field, field_validator
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser
from app.core.db import DbSession
from app.models import Listing, User
from app.models import Meetup as MeetupRow
from app.models import MeetupEvent as MeetupEventRow
from app.schemas import ApiModel

router = APIRouter(prefix="/meetups", tags=["meetups"])

MeetupStatus = Literal["pending", "accepted", "declined", "cancelled"]
MeetupAction = Literal["accept", "counter", "decline", "cancel"]
MeetupEventKind = Literal["propose", "counter", "accept", "decline", "cancel"]
MeetupRole = Literal["borrower", "lender"]


class MeetupTerms(ApiModel):
    meet_at: datetime = Field(description="When to meet, as an ISO timestamp with an offset.")
    location: str = Field(min_length=1, max_length=200, description="Where to meet.")
    price: Decimal = Field(
        ge=0, max_digits=10, decimal_places=2, description="Offered price in SGD."
    )
    message: str | None = Field(default=None, max_length=500)

    @field_validator("meet_at")
    @classmethod
    def in_the_future(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("meet_at needs a timezone offset")
        if value <= datetime.now(UTC):
            raise ValueError("meet_at must be in the future")
        return value

    @field_validator("location")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("location must not be blank")
        return value.strip()


class MeetupCreate(MeetupTerms):
    listing_id: UUID


class MeetupNote(ApiModel):
    message: str | None = Field(default=None, max_length=500)


class MeetupEvent(ApiModel):
    id: UUID
    author_id: UUID
    author_display_name: str
    kind: MeetupEventKind
    meet_at: datetime | None = None
    location: str | None = None
    price: Decimal | None = None
    message: str | None = None
    created_at: datetime


class Meetup(ApiModel):
    id: UUID
    listing_id: UUID
    listing_title: str
    borrower_id: UUID
    borrower_display_name: str
    lender_id: UUID
    lender_display_name: str
    status: MeetupStatus
    meet_at: datetime
    location: str
    price: Decimal
    proposed_by: UUID
    awaiting_role: MeetupRole | None = Field(
        description="Who must respond next; null once the meetup is no longer open."
    )
    viewer_role: MeetupRole
    available_actions: list[MeetupAction]
    events: list[MeetupEvent]
    created_at: datetime
    updated_at: datetime


# --- Rules -------------------------------------------------------------------


def available_actions(meetup: MeetupRow, viewer_id: UUID, now: datetime) -> list[MeetupAction]:
    if meetup.status == "pending":
        if viewer_id == meetup.proposed_by:
            return ["cancel"]
        # A proposed time that has already passed can only be replaced or turned down.
        return ["accept", "counter", "decline"] if meetup.meet_at > now else ["counter", "decline"]
    if meetup.status == "accepted" and meetup.meet_at > now:
        return ["cancel"]
    return []


def _refusal(meetup: MeetupRow, viewer_id: UUID, action: MeetupAction) -> str:
    if action == "cancel":
        return "Only your own open proposal or an upcoming meeting can be cancelled"
    if meetup.status != "pending":
        return f"This meetup is already {meetup.status}"
    if viewer_id == meetup.proposed_by:
        return "Waiting for the other person to respond to your offer"
    return "That time has passed. Counter with a new time instead."


def _require(meetup: MeetupRow, viewer_id: UUID, action: MeetupAction) -> None:
    if action not in available_actions(meetup, viewer_id, datetime.now(UTC)):
        raise HTTPException(status.HTTP_409_CONFLICT, _refusal(meetup, viewer_id, action))


# --- Reading -----------------------------------------------------------------


async def _views(db: AsyncSession, meetups: list[MeetupRow], viewer_id: UUID) -> list[Meetup]:
    if not meetups:
        return []
    ids = [m.id for m in meetups]
    events = list(
        await db.scalars(
            select(MeetupEventRow)
            .where(MeetupEventRow.meetup_id.in_(ids))
            .order_by(MeetupEventRow.created_at, MeetupEventRow.id)
        )
    )
    titles = dict(
        (
            await db.execute(
                select(Listing.id, Listing.title).where(
                    Listing.id.in_({m.listing_id for m in meetups})
                )
            )
        ).all()
    )
    people = {m.borrower_id for m in meetups} | {m.lender_id for m in meetups}
    people |= {e.author_id for e in events}
    names = dict(
        (await db.execute(select(User.id, User.display_name).where(User.id.in_(people)))).all()
    )
    by_meetup: dict[UUID, list[MeetupEvent]] = {m.id: [] for m in meetups}
    for event in events:
        by_meetup[event.meetup_id].append(
            MeetupEvent(
                id=event.id,
                author_id=event.author_id,
                author_display_name=names[event.author_id],
                kind=event.kind,
                meet_at=event.meet_at,
                location=event.location,
                price=event.price,
                message=event.message,
                created_at=event.created_at,
            )
        )
    now = datetime.now(UTC)
    views = []
    for m in meetups:
        awaiting: MeetupRole | None = None
        if m.status == "pending":
            awaiting = "lender" if m.proposed_by == m.borrower_id else "borrower"
        views.append(
            Meetup(
                id=m.id,
                listing_id=m.listing_id,
                listing_title=titles[m.listing_id],
                borrower_id=m.borrower_id,
                borrower_display_name=names[m.borrower_id],
                lender_id=m.lender_id,
                lender_display_name=names[m.lender_id],
                status=m.status,
                meet_at=m.meet_at,
                location=m.location,
                price=m.price,
                proposed_by=m.proposed_by,
                awaiting_role=awaiting,
                viewer_role="borrower" if viewer_id == m.borrower_id else "lender",
                available_actions=available_actions(m, viewer_id, now),
                events=by_meetup[m.id],
                created_at=m.created_at,
                updated_at=m.updated_at,
            )
        )
    return views


async def _fetch(db: AsyncSession, meetup_id: UUID, viewer_id: UUID, lock: bool) -> MeetupRow:
    query = select(MeetupRow).where(MeetupRow.id == meetup_id)
    if lock:
        query = query.with_for_update()
    meetup = await db.scalar(query.execution_options(populate_existing=True))
    if meetup is None or viewer_id not in (meetup.borrower_id, meetup.lender_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Meetup not found")
    return meetup


async def _view(db: AsyncSession, meetup_id: UUID, viewer_id: UUID) -> Meetup:
    return (await _views(db, [await _fetch(db, meetup_id, viewer_id, lock=False)], viewer_id))[0]


def _record(
    db: AsyncSession,
    meetup: MeetupRow,
    author_id: UUID,
    kind: MeetupEventKind,
    message: str | None,
    with_terms: bool = False,
) -> None:
    db.add(
        MeetupEventRow(
            meetup_id=meetup.id,
            author_id=author_id,
            kind=kind,
            meet_at=meetup.meet_at if with_terms else None,
            location=meetup.location if with_terms else None,
            price=meetup.price if with_terms else None,
            message=(message or "").strip() or None,
        )
    )


# --- Endpoints ---------------------------------------------------------------


@router.post(
    "",
    response_model=Meetup,
    status_code=status.HTTP_201_CREATED,
    operation_id="createMeetup",
    responses={
        400: {"description": "Proposing to meet about your own listing"},
        404: {"description": "Listing not found or not active"},
        409: {"description": "You already have an open proposal for this listing"},
    },
)
async def create_meetup(request: MeetupCreate, user: CurrentUser, db: DbSession) -> Meetup:
    """A borrower proposes a time, place and price to the lender of an active listing."""
    listing = await db.get(Listing, request.listing_id)
    if listing is None or listing.status != "active":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Listing is no longer available")
    if listing.owner_id == user.id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "You can't propose a meetup for your own listing"
        )
    meetup = MeetupRow(
        listing_id=listing.id,
        borrower_id=user.id,
        lender_id=listing.owner_id,
        meet_at=request.meet_at,
        location=request.location,
        price=request.price,
        proposed_by=user.id,
    )
    db.add(meetup)
    try:
        await db.flush()
    except IntegrityError as error:
        await db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "You already have an open proposal for this listing. Check your Meetings.",
        ) from error
    _record(db, meetup, user.id, "propose", request.message, with_terms=True)
    await db.commit()
    return await _view(db, meetup.id, user.id)


@router.get("", response_model=list[Meetup], operation_id="listMeetups")
async def list_meetups(
    user: CurrentUser,
    db: DbSession,
    role: MeetupRole | None = None,
    state: Annotated[MeetupStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[Meetup]:
    """The caller's meetups as borrower, lender or both, most recently updated first."""
    query = select(MeetupRow)
    if role == "borrower":
        query = query.where(MeetupRow.borrower_id == user.id)
    elif role == "lender":
        query = query.where(MeetupRow.lender_id == user.id)
    else:
        query = query.where(or_(MeetupRow.borrower_id == user.id, MeetupRow.lender_id == user.id))
    if state:
        query = query.where(MeetupRow.status == state)
    rows = await db.scalars(query.order_by(MeetupRow.updated_at.desc(), MeetupRow.id).limit(limit))
    return await _views(db, list(rows), user.id)


@router.get("/{meetup_id}", response_model=Meetup, operation_id="getMeetup")
async def get_meetup(meetup_id: UUID, user: CurrentUser, db: DbSession) -> Meetup:
    return await _view(db, meetup_id, user.id)


@router.post("/{meetup_id}/counter", response_model=Meetup, operation_id="counterMeetup")
async def counter_meetup(
    meetup_id: UUID, request: MeetupTerms, user: CurrentUser, db: DbSession
) -> Meetup:
    """Replace the terms on the table; the other person now has to respond."""
    meetup = await _fetch(db, meetup_id, user.id, lock=True)
    _require(meetup, user.id, "counter")
    meetup.meet_at = request.meet_at
    meetup.location = request.location
    meetup.price = request.price
    meetup.proposed_by = user.id
    meetup.updated_at = datetime.now(UTC)
    _record(db, meetup, user.id, "counter", request.message, with_terms=True)
    await db.commit()
    return await _view(db, meetup.id, user.id)


async def _close(
    db: AsyncSession,
    meetup_id: UUID,
    user_id: UUID,
    action: MeetupAction,
    new_status: MeetupStatus,
    note: MeetupNote | None,
) -> Meetup:
    meetup = await _fetch(db, meetup_id, user_id, lock=True)
    _require(meetup, user_id, action)
    meetup.status = new_status
    meetup.updated_at = datetime.now(UTC)
    _record(db, meetup, user_id, action, note.message if note else None)
    await db.commit()
    return await _view(db, meetup.id, user_id)


@router.post("/{meetup_id}/accept", response_model=Meetup, operation_id="acceptMeetup")
async def accept_meetup(
    meetup_id: UUID, user: CurrentUser, db: DbSession, note: MeetupNote | None = None
) -> Meetup:
    """Agree to the terms on the table. Both sides have now agreed: the meeting is scheduled."""
    return await _close(db, meetup_id, user.id, "accept", "accepted", note)


@router.post("/{meetup_id}/decline", response_model=Meetup, operation_id="declineMeetup")
async def decline_meetup(
    meetup_id: UUID, user: CurrentUser, db: DbSession, note: MeetupNote | None = None
) -> Meetup:
    """Turn down the offer and close the negotiation."""
    return await _close(db, meetup_id, user.id, "decline", "declined", note)


@router.post("/{meetup_id}/cancel", response_model=Meetup, operation_id="cancelMeetup")
async def cancel_meetup(
    meetup_id: UUID, user: CurrentUser, db: DbSession, note: MeetupNote | None = None
) -> Meetup:
    """Withdraw your own open offer, or call off a scheduled meeting before it happens."""
    return await _close(db, meetup_id, user.id, "cancel", "cancelled", note)


async def cancel_open_meetups(db: AsyncSession, user_id: UUID, message: str) -> None:
    """Close every open or upcoming meetup the user is part of (used by account deletion).
    The caller commits."""
    rows = await db.scalars(
        select(MeetupRow)
        .where(
            or_(MeetupRow.borrower_id == user_id, MeetupRow.lender_id == user_id),
            MeetupRow.status.in_(("pending", "accepted")),
        )
        .with_for_update()
    )
    now = datetime.now(UTC)
    for meetup in rows:
        meetup.status = "cancelled"
        meetup.updated_at = now
        _record(db, meetup, user_id, "cancel", message)
