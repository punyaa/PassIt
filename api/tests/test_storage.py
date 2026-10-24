from urllib.parse import parse_qs, urlparse

import pytest

from app.core.config import Settings
from app.integrations.storage import S3Storage


@pytest.fixture(autouse=True)
def offline_aws_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIAEXAMPLEEXAMPLE")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "example-secret-example-secret-example")
    monkeypatch.delenv("AWS_PROFILE", raising=False)


def test_presigned_upload_is_sigv4_on_the_regional_endpoint() -> None:
    storage = S3Storage(Settings(s3_bucket="passit-media", aws_region="ap-southeast-1"))
    upload = storage.presign_upload("media/listing/u/k.jpg", "image/jpeg")
    url = urlparse(upload.upload_url)
    # A global-endpoint URL gets a 307 redirect, which browsers refuse on a cross-origin PUT.
    assert url.hostname == "passit-media.s3.ap-southeast-1.amazonaws.com"
    assert parse_qs(url.query)["X-Amz-Algorithm"] == ["AWS4-HMAC-SHA256"]
    assert upload.headers == {"content-type": "image/jpeg"}
