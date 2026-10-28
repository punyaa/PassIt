"""Media keys and records. Keys are namespaced `<prefix><stage>/<uploader id>/<uuid><ext>`,
so the API can check that a client only attaches files it was allowed to upload."""

from collections import defaultdict
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.integrations.storage import EXTENSIONS, get_storage
from app.models import Media


def key_prefix(stage: str, user_id: UUID) -> str:
    return f"{get_settings().s3_prefix}{stage}/{user_id}/"


def new_key(stage: str, user_id: UUID, content_type: str) -> str:
    return f"{key_prefix(stage, user_id)}{uuid4()}{EXTENSIONS[content_type]}"


def require_owned_keys(keys: list[str], stage: str, user_id: UUID) -> None:
    prefix = key_prefix(stage, user_id)
    for key in keys:
        if not key.startswith(prefix) or ".." in key:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, f"Media key {key} was not issued for this {stage}"
            )


async def attach_media(
    db: AsyncSession,
    keys: list[str],
    stage: str,
    user_id: UUID,
    *,
    listing_id: UUID | None = None,
    booking_id: UUID | None = None,
) -> list[Media]:
    """Record uploaded objects. Evidence is append-only: a key can be attached once."""
    require_owned_keys(keys, stage, user_id)
    if len(set(keys)) != len(keys):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Duplicate media keys")
    taken = await db.scalars(select(Media.s3_key).where(Media.s3_key.in_(keys)))
    if taken.first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Media already attached")
    start = 0
    if stage == "listing":
        start = await db.scalar(
            select(func.coalesce(func.max(Media.position) + 1, 0)).where(
                Media.listing_id == listing_id, Media.stage == "listing"
            )
        )
    rows = [
        Media(
            s3_key=key,
            position=start + position,
            stage=stage,
            uploaded_by=user_id,
            listing_id=listing_id,
            booking_id=booking_id,
        )
        for position, key in enumerate(keys)
    ]
    db.add_all(rows)
    await db.flush()
    return rows


async def listing_photo_urls(db: AsyncSession, listing_ids: list[UUID]) -> dict[UUID, list[str]]:
    if not listing_ids:
        return {}
    rows = await db.scalars(
        select(Media)
        .where(Media.listing_id.in_(listing_ids), Media.stage == "listing")
        .order_by(Media.position, Media.created_at, Media.id)
    )
    storage = get_storage()
    urls: dict[UUID, list[str]] = defaultdict(list)
    for media in rows:
        urls[media.listing_id].append(storage.view_url(media.s3_key))
    return urls
