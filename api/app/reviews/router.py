from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.auth.dependencies import CurrentUser
from app.bookings.state_machine import REVIEWABLE_STATES
from app.core.db import DbSession
from app.models import Booking, Listing, User
from app.models import Review as ReviewRow
from app.schemas import ApiModel

router = APIRouter(prefix="/reviews", tags=["reviews"])


class ReviewCreate(ApiModel):
    booking_id: UUID
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=1000)


class Review(ApiModel):
    id: UUID
    booking_id: UUID
    author_id: UUID
    author_display_name: str
    target_id: UUID
    rating: int
    comment: str | None = None
    created_at: datetime


def _to_response(review: ReviewRow, author_name: str) -> Review:
    return Review(
        id=review.id,
        booking_id=review.booking_id,
        author_id=review.author_id,
        author_display_name=author_name,
        target_id=review.target_id,
        rating=review.rating,
        comment=review.comment,
        created_at=review.created_at,
    )


@router.post(
    "", response_model=Review, status_code=status.HTTP_201_CREATED, operation_id="createReview"
)
async def create_review(request: ReviewCreate, user: CurrentUser, db: DbSession) -> Review:
    """Two-sided: the borrower reviews the lender and the lender reviews the borrower,
    once each per booking, after the item is returned."""
    booking = await db.get(Booking, request.booking_id)
    listing = booking and await db.get(Listing, booking.listing_id)
    if booking is None or user.id not in (booking.borrower_id, listing.owner_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found")
    if booking.state not in REVIEWABLE_STATES:
        raise HTTPException(status.HTTP_409_CONFLICT, "Reviews open once the item is returned")
    target_id = listing.owner_id if user.id == booking.borrower_id else booking.borrower_id
    review = ReviewRow(
        booking_id=booking.id,
        author_id=user.id,
        target_id=target_id,
        rating=request.rating,
        comment=request.comment,
    )
    db.add(review)
    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "You already reviewed this booking"
        ) from error
    await db.refresh(review)
    return _to_response(review, user.display_name)


@router.get("", response_model=list[Review], operation_id="listReviews")
async def list_reviews(
    db: DbSession,
    user_id: UUID,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[Review]:
    """Reviews received by a user, newest first."""
    rows = await db.execute(
        select(ReviewRow, User.display_name)
        .join(User, User.id == ReviewRow.author_id)
        .where(ReviewRow.target_id == user_id)
        .order_by(ReviewRow.created_at.desc())
        .limit(limit)
    )
    return [_to_response(review, name) for review, name in rows]
