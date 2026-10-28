"""Creates a small JPEG thumbnail for every listing photo uploaded to S3.

S3 calls this function for each new object under `media/listing/`. It writes
`thumbs/listing/<user>/<id>.jpg` beside the original, never over it. The listing cards use
the thumbnail, so a page of results downloads kilobytes instead of full camera photos.

Only listing photos are thumbnailed. Handover and return photos are damage evidence and are
served exactly as uploaded.

Rules:
- Skips anything that is not a JPEG or PNG, anything over MAX_SOURCE_BYTES, and anything
  that is not a readable image (logged, not retried, because retrying cannot fix it).
- Applies the photo's EXIF rotation, then drops all metadata, so a thumbnail never carries
  the GPS position of a lender's home.
- The output key never matches the trigger prefix, so the function cannot trigger itself.

The key rule mirrors `thumbnail_key` in api/app/integrations/storage.py; a test keeps the two
in step. Settings come from environment variables set by Terraform.
"""

import io
import logging
import os
import urllib.parse
from typing import Any

from PIL import Image, ImageOps, UnidentifiedImageError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

MEDIA_PREFIX = os.environ.get("MEDIA_PREFIX", "media/")
THUMBNAIL_PREFIX = os.environ.get("THUMBNAIL_PREFIX", "thumbs/")
MAX_EDGE = int(os.environ.get("THUMBNAIL_MAX_EDGE", "640"))
QUALITY = int(os.environ.get("THUMBNAIL_QUALITY", "82"))
MAX_SOURCE_BYTES = int(os.environ.get("MAX_SOURCE_BYTES", str(25 * 1024 * 1024)))
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png")

# Larger than any camera photo, so a decompression bomb is refused instead of decoded.
Image.MAX_IMAGE_PIXELS = 60_000_000

_client: Any = None


def _s3() -> Any:
    global _client
    if _client is None:
        import boto3  # noqa: PLC0415 - provided by the Lambda runtime

        _client = boto3.client("s3")
    return _client


def thumbnail_key(key: str) -> str:
    """`media/listing/<user>/<id>.png` becomes `thumbs/listing/<user>/<id>.jpg`."""
    relative = key.removeprefix(MEDIA_PREFIX)
    head, _, name = relative.rpartition("/")
    stem = name.rpartition(".")[0] or name
    return f"{THUMBNAIL_PREFIX}{head + '/' if head else ''}{stem}.jpg"


def should_process(key: str, size: int) -> bool:
    return (
        key.startswith(f"{MEDIA_PREFIX}listing/")
        and key.lower().endswith(IMAGE_EXTENSIONS)
        and size <= MAX_SOURCE_BYTES
    )


def make_thumbnail(data: bytes) -> bytes:
    """A JPEG no larger than MAX_EDGE on its longest side, with no metadata."""
    with Image.open(io.BytesIO(data)) as opened:
        image = ImageOps.exif_transpose(opened)
        has_alpha = image.mode in ("RGBA", "LA") or (
            image.mode == "P" and "transparency" in image.info
        )
        if has_alpha:
            # JPEG has no transparency; flatten onto white rather than black.
            rgba = image.convert("RGBA")
            flat = Image.new("RGB", rgba.size, (255, 255, 255))
            flat.paste(rgba, mask=rgba.getchannel("A"))
            image = flat
        else:
            image = image.convert("RGB")
        image.thumbnail((MAX_EDGE, MAX_EDGE), Image.Resampling.LANCZOS)
        out = io.BytesIO()
        image.save(out, "JPEG", quality=QUALITY, optimize=True, progressive=True)
        return out.getvalue()


def handler(event: dict[str, Any], context: Any = None) -> dict[str, int]:
    created = skipped = 0
    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        key = urllib.parse.unquote_plus(record["s3"]["object"]["key"])
        size = record["s3"]["object"].get("size", 0)
        if not should_process(key, size):
            logger.info("skipping %s", key)
            skipped += 1
            continue
        # An S3 error here is transient, so let it raise and S3 retries the event.
        original = _s3().get_object(Bucket=bucket, Key=key)["Body"].read()
        try:
            thumbnail = make_thumbnail(original)
        except (UnidentifiedImageError, Image.DecompressionBombError, OSError, ValueError) as error:
            logger.warning("not a readable image, skipping %s: %s", key, error)
            skipped += 1
            continue
        _s3().put_object(
            Bucket=bucket,
            Key=thumbnail_key(key),
            Body=thumbnail,
            ContentType="image/jpeg",
            # The key holds a fresh uuid per upload, so the thumbnail never changes.
            CacheControl="public, max-age=31536000, immutable",
        )
        logger.info("thumbnail %s -> %s (%d bytes)", key, thumbnail_key(key), len(thumbnail))
        created += 1
    return {"created": created, "skipped": skipped}
