from typing import Literal

from fastapi import APIRouter

from app.core.stubs import not_implemented
from app.schemas import ApiModel

router = APIRouter(prefix="/media", tags=["media"])


class PresignRequest(ApiModel):
    stage: Literal["listing", "handover", "return"]
    content_type: Literal["image/jpeg", "image/png", "video/mp4"]


class PresignResponse(ApiModel):
    upload_url: str
    key: str
    expires_in_seconds: int


@router.post("/presign", response_model=PresignResponse, operation_id="presignMediaUpload")
async def presign_media_upload(_: PresignRequest) -> PresignResponse:
    not_implemented("S3 signed media upload", "B3 Catalogue")
