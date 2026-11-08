"""Photo thumbnails: the key rule, the Lambda that makes them, and the URLs the API returns."""

import io

import pytest
from PIL import Image

from app.core.config import Settings
from app.integrations.storage import LocalStorage, S3Storage, thumbnail_key
from tests.helpers import create_listing, upload
from tests.lambda_modules import load

pytestmark = pytest.mark.anyio

KEYS = [
    "media/listing/u1/abc.png",
    "media/listing/u1/abc.jpg",
    "media/listing/u1/abc.JPEG",
    "media/listing/u1/no-extension",
    "media/listing/deep/er/path/x.y.png",
]


@pytest.fixture
def thumbnailer(monkeypatch):
    return load("thumbnailer", monkeypatch)


def picture(size=(2000, 1000), mode="RGB", fmt="JPEG", **save) -> bytes:
    out = io.BytesIO()
    Image.new(mode, size, (200, 30, 30) if mode == "RGB" else (200, 30, 30, 0)).save(
        out, fmt, **save
    )
    return out.getvalue()


@pytest.mark.parametrize("key", KEYS)
def test_lambda_and_api_agree_on_the_thumbnail_key(thumbnailer, key):
    assert thumbnailer.thumbnail_key(key) == thumbnail_key(
        key, media_prefix="media/", thumbnail_prefix="thumbs/"
    )


def test_thumbnail_key_examples():
    rule = {"media_prefix": "media/", "thumbnail_prefix": "thumbs/"}
    assert thumbnail_key("media/listing/u1/abc.png", **rule) == "thumbs/listing/u1/abc.jpg"
    assert (
        thumbnail_key("media/listing/u1/no-extension", **rule)
        == "thumbs/listing/u1/no-extension.jpg"
    )


def test_thumbnail_fits_the_box_and_keeps_the_aspect_ratio(thumbnailer):
    result = Image.open(io.BytesIO(thumbnailer.make_thumbnail(picture((2000, 1000)))))
    assert result.format == "JPEG" and result.size == (640, 320)
    tall = Image.open(io.BytesIO(thumbnailer.make_thumbnail(picture((600, 1800)))))
    assert tall.size == (213, 640)


def test_a_small_photo_is_not_enlarged(thumbnailer):
    result = Image.open(io.BytesIO(thumbnailer.make_thumbnail(picture((100, 50)))))
    assert result.size == (100, 50)


def test_transparent_png_is_flattened_onto_white(thumbnailer):
    transparent = picture((50, 50), mode="RGBA", fmt="PNG")
    result = Image.open(io.BytesIO(thumbnailer.make_thumbnail(transparent)))
    assert result.mode == "RGB" and min(result.getpixel((25, 25))) >= 250


def test_metadata_such_as_gps_is_dropped(thumbnailer):
    exif = Image.Exif()
    exif[0x010F] = "SecretCamera"
    original = picture((300, 200), exif=exif.tobytes())
    assert Image.open(io.BytesIO(original)).getexif().get(0x010F) == "SecretCamera"
    result = Image.open(io.BytesIO(thumbnailer.make_thumbnail(original)))
    assert dict(result.getexif()) == {}


def test_exif_rotation_is_applied_before_the_metadata_goes(thumbnailer):
    exif = Image.Exif()
    exif[0x0112] = 6  # stored sideways: displayed rotated by 90 degrees
    original = picture((400, 200), exif=exif.tobytes())
    result = Image.open(io.BytesIO(thumbnailer.make_thumbnail(original)))
    assert result.size == (200, 400)


class FakeS3:
    def __init__(self, objects: dict[str, bytes]) -> None:
        self.objects, self.put = objects, {}

    def get_object(self, Bucket, Key):  # noqa: N803 - boto3's names
        return {"Body": io.BytesIO(self.objects[Key])}

    def put_object(self, **kwargs):
        self.put[kwargs["Key"]] = kwargs


def s3_event(key: str, size: int = 1000) -> dict:
    return {"Records": [{"s3": {"bucket": {"name": "b"}, "object": {"key": key, "size": size}}}]}


def test_handler_writes_the_thumbnail_next_to_the_original(thumbnailer, monkeypatch):
    s3 = FakeS3({"media/listing/u 1/abc.png": picture((800, 800), fmt="PNG")})
    monkeypatch.setattr(thumbnailer, "_s3", lambda: s3)

    # S3 sends the key URL-encoded: a space arrives as "+".
    result = thumbnailer.handler(s3_event("media/listing/u+1/abc.png"))

    assert result == {"created": 1, "skipped": 0}
    written = s3.put["thumbs/listing/u 1/abc.jpg"]
    assert written["ContentType"] == "image/jpeg" and "immutable" in written["CacheControl"]
    assert "media/listing/u 1/abc.png" in s3.objects  # the original is untouched


@pytest.mark.parametrize(
    "key,size",
    [
        ("media/handover/u1/abc.png", 1000),  # evidence is served as uploaded
        ("media/return/u1/abc.jpg", 1000),
        ("media/listing/u1/clip.mp4", 1000),  # not an image
        ("thumbs/listing/u1/abc.jpg", 1000),  # never react to our own output
        ("media/listing/u1/huge.jpg", 99_000_000),  # over MAX_SOURCE_BYTES
    ],
)
def test_handler_skips_what_is_not_a_listing_photo(thumbnailer, monkeypatch, key, size):
    s3 = FakeS3({})
    monkeypatch.setattr(thumbnailer, "_s3", lambda: s3)
    assert thumbnailer.handler(s3_event(key, size)) == {"created": 0, "skipped": 1}
    assert s3.put == {}


def test_handler_skips_a_file_that_is_not_an_image_without_failing(thumbnailer, monkeypatch):
    s3 = FakeS3({"media/listing/u1/fake.jpg": b"this is not a picture"})
    monkeypatch.setattr(thumbnailer, "_s3", lambda: s3)
    assert thumbnailer.handler(s3_event("media/listing/u1/fake.jpg")) == {
        "created": 0,
        "skipped": 1,
    }


def test_storage_urls_point_at_the_thumbnail():
    s3 = S3Storage.__new__(S3Storage)
    s3.settings = Settings(
        s3_bucket="b", cloudfront_domain="d1.cloudfront.net", thumbnail_prefix="thumbs/"
    )
    assert (
        s3.thumbnail_url("media/listing/u1/abc.png")
        == "https://d1.cloudfront.net/thumbs/listing/u1/abc.jpg"
    )
    local = LocalStorage(Settings(public_api_url="http://x"))
    key = "media/listing/u1/abc.png"
    assert local.thumbnail_url(key) == local.view_url(key)  # no thumbnailer locally


async def test_listings_carry_thumbnail_urls_in_step_with_photos(client, make_user):
    lender = make_user("Lena")
    keys = [await upload(client, lender, "listing") for _ in range(2)]
    listing = await create_listing(client, lender, photo_keys=keys)
    for shown in (listing, (await client.get(f"/listings/{listing['id']}")).json()):
        assert len(shown["photo_urls"]) == len(shown["thumbnail_urls"]) == 2
    searched = (await client.get("/listings")).json()
    assert [len(card["thumbnail_urls"]) for card in searched] == [2]
