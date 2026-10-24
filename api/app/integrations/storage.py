"""Media storage: signed direct uploads and viewing URLs.

The API never proxies file bytes in AWS: the browser PUTs straight to S3 with a
presigned URL. Locally, `LocalStorage` imitates that flow with a signed PUT to the API
(see `app/media/local_router.py`) so the frontend works without an AWS account.

Switch with PASSIT_STORAGE_BACKEND=local|s3.

Platform/B3 hand-off for S3 (see api/README.md, "AWS hand-off"):
  1. Terraform the bucket (block public access, CORS allowing PUT from the web origin),
     optionally a CloudFront distribution with Origin Access Control.
  2. Grant the ECS task role s3:PutObject and s3:GetObject on `<bucket>/<prefix>*`.
  3. `uv add --project api boto3`, set PASSIT_S3_BUCKET (+ PASSIT_CLOUDFRONT_DOMAIN).
  4. Set PASSIT_STORAGE_BACKEND=s3 and run the upload flow once on staging.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Protocol

import jwt

from app.core.config import Settings, get_settings

EXTENSIONS = {"image/jpeg": ".jpg", "image/png": ".png", "video/mp4": ".mp4"}


@dataclass(frozen=True)
class PresignedUpload:
    upload_url: str
    expires_in_seconds: int
    headers: dict[str, str]


class MediaStorage(Protocol):
    def presign_upload(self, key: str, content_type: str) -> PresignedUpload: ...

    def view_url(self, key: str) -> str: ...


class LocalStorage:
    """Development-only: uploads land in PASSIT_LOCAL_MEDIA_DIR via the API."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def presign_upload(self, key: str, content_type: str) -> PresignedUpload:
        ttl = self.settings.media_signed_url_ttl_seconds
        token = jwt.encode(
            {"key": key, "ct": content_type, "exp": datetime.now(UTC) + timedelta(seconds=ttl)},
            self.settings.jwt_secret,
            algorithm="HS256",
        )
        return PresignedUpload(
            upload_url=f"{self.settings.public_api_url}/v1/media/local/{key}?token={token}",
            expires_in_seconds=ttl,
            headers={"content-type": content_type},
        )

    def view_url(self, key: str) -> str:
        return f"{self.settings.public_api_url}/v1/media/local/{key}"


class S3Storage:
    """AWS implementation, verified against the staging bucket."""

    def __init__(self, settings: Settings) -> None:
        if not settings.s3_bucket:
            raise RuntimeError("PASSIT_S3_BUCKET is required when PASSIT_STORAGE_BACKEND=s3")
        try:
            import boto3  # noqa: PLC0415 - optional dependency until AWS is provisioned
            from botocore.config import Config  # noqa: PLC0415
        except ImportError as error:
            raise RuntimeError("Add boto3: `uv add --project api boto3`") from error
        session = boto3.Session(profile_name=settings.aws_profile or None)
        # SigV4 against the regional endpoint. The default presigns with SigV2 against the
        # global endpoint, which S3 answers with a 307 redirect that a browser refuses to
        # follow on a cross-origin PUT.
        self.client = session.client(
            "s3",
            region_name=settings.aws_region,
            config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}),
        )
        self.settings = settings

    def presign_upload(self, key: str, content_type: str) -> PresignedUpload:
        ttl = self.settings.media_signed_url_ttl_seconds
        url = self.client.generate_presigned_url(
            "put_object",
            Params={"Bucket": self.settings.s3_bucket, "Key": key, "ContentType": content_type},
            ExpiresIn=ttl,
        )
        return PresignedUpload(url, ttl, {"content-type": content_type})

    def view_url(self, key: str) -> str:
        # TODO: condition evidence is private. If CloudFront serves media, switch this to
        # CloudFront signed URLs (botocore.signers.CloudFrontSigner) rather than public paths.
        if self.settings.cloudfront_domain:
            return f"https://{self.settings.cloudfront_domain}/{key}"
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.settings.s3_bucket, "Key": key},
            ExpiresIn=self.settings.media_signed_url_ttl_seconds,
        )


@lru_cache
def get_storage() -> MediaStorage:
    settings = get_settings()
    if settings.storage_backend == "s3":
        return S3Storage(settings)
    return LocalStorage(settings)
