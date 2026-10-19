from uuid import UUID

from fastapi import APIRouter

from app.core.stubs import not_implemented
from app.schemas import ApiModel

router = APIRouter(prefix="/reviews", tags=["reviews"])


class ReviewCreate(ApiModel):
    booking_id: UUID
    target_id: UUID
    rating: int
    comment: str | None = None


class Review(ApiModel):
    id: UUID
    booking_id: UUID
    author_id: UUID
    target_id: UUID
    rating: int
    comment: str | None = None


@router.post("", response_model=Review, operation_id="createReview")
async def create_review(_: ReviewCreate) -> Review:
    not_implemented("two-sided reviews", "B1 Booking")
