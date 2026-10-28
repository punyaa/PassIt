"""Public lender identity never includes account email or credentials."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select

from app.core.db import DbSession
from app.integrations.storage import get_storage
from app.models import Review, User
from app.schemas import ApiModel

router = APIRouter(prefix="/users", tags=["profiles"])


class PublicProfile(ApiModel):
    user_id: UUID
    display_name: str
    bio: str | None
    avatar_url: str | None
    member_since: datetime
    rating: float | None
    review_count: int


@router.get("/{user_id}", response_model=PublicProfile, operation_id="getPublicProfile")
async def get_public_profile(user_id: UUID, db: DbSession) -> PublicProfile:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "Profile not found")
    rating, count = (
        await db.execute(
            select(func.avg(Review.rating), func.count(Review.id)).where(
                Review.target_id == user_id
            )
        )
    ).one()
    return PublicProfile(
        user_id=user.id,
        display_name=user.display_name,
        bio=user.bio,
        avatar_url=get_storage().view_url(user.avatar_key) if user.avatar_key else None,
        member_since=user.created_at,
        rating=round(float(rating), 2) if rating else None,
        review_count=count,
    )
