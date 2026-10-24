from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.auth.dependencies import CurrentUser
from app.core.db import DbSession
from app.integrations.storage import get_storage
from app.media.service import attach_media, new_key
from app.models import Listing
from app.schemas import ApiModel

router = APIRouter(prefix="/media", tags=["media"])

MediaStage = Literal["listing", "handover", "return"]


class PresignRequest(ApiModel):
    stage: MediaStage
    content_type: Literal["image/jpeg", "image/png", "video/mp4"]


class PresignResponse(ApiModel):
    upload_url: str
    key: str
    expires_in_seconds: int
    headers: dict[str, str]


class MediaCreate(ApiModel):
    key: str
    listing_id: UUID


class MediaRecord(ApiModel):
    id: UUID
    key: str
    stage: MediaStage
    url: str


@router.post("/presign", response_model=PresignResponse, operation_id="presignMediaUpload")
async def presign_media_upload(request: PresignRequest, user: CurrentUser) -> PresignResponse:
    """Issue a short-lived direct-upload URL. PUT the file there with the given headers,
    then attach the key to a listing (`POST /media`, or `photo_keys` on listing creation)
    or to a handover/return checklist (`media_keys`)."""
    key = new_key(request.stage, user.id, request.content_type)
    upload = get_storage().presign_upload(key, request.content_type)
    return PresignResponse(
        upload_url=upload.upload_url,
        key=key,
        expires_in_seconds=upload.expires_in_seconds,
        headers=upload.headers,
    )


@router.post(
    "",
    response_model=MediaRecord,
    status_code=status.HTTP_201_CREATED,
    operation_id="attachListingMedia",
)
async def attach_listing_media(
    request: MediaCreate, user: CurrentUser, db: DbSession
) -> MediaRecord:
    """Attach an uploaded photo to one of your listings. Booking evidence is attached
    through the handover and return checklists instead."""
    listing = await db.get(Listing, request.listing_id)
    if listing is None or listing.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Listing not found")
    [media] = await attach_media(db, [request.key], "listing", user.id, listing_id=listing.id)
    await db.commit()
    return MediaRecord(
        id=media.id, key=media.s3_key, stage="listing", url=get_storage().view_url(media.s3_key)
    )
