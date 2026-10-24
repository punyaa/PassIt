"""Local stand-in for S3, active only when PASSIT_STORAGE_BACKEND=local.

Mimics presigned PUT semantics: the upload URL carries a signed, expiring token bound to
one key and content type. Hidden from the OpenAPI contract because clients only ever
follow the URL returned by `POST /media/presign`.
"""

from pathlib import Path

import jwt
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import FileResponse, Response

from app.core.config import get_settings

router = APIRouter(prefix="/media/local", include_in_schema=False)


def _path_for(key: str) -> Path:
    settings = get_settings()
    if settings.storage_backend != "local":
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    root = Path(settings.local_media_dir).resolve()
    path = (root / key).resolve()
    if not path.is_relative_to(root):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid key")
    return path


@router.put("/{key:path}", status_code=status.HTTP_200_OK)
async def upload(key: str, token: str, request: Request) -> Response:
    path = _path_for(key)
    try:
        claims = jwt.decode(token, get_settings().jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError as error:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Upload URL expired or invalid") from error
    if claims.get("key") != key or claims.get("ct") != request.headers.get("content-type"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Upload URL does not match this file")
    if path.exists():
        raise HTTPException(status.HTTP_409_CONFLICT, "Media is write-once")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(await request.body())
    return Response(status_code=status.HTTP_200_OK)


@router.get("/{key:path}")
async def download(key: str) -> FileResponse:
    path = _path_for(key)
    if not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    return FileResponse(path)
