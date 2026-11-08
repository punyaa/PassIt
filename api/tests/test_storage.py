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


def _rsa_private_key_pem() -> str:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return (
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        .decode()
        .replace("\n", "\\n")
    )  # escaped, as the key arrives in an environment variable


def test_cloudfront_view_url_is_signed_when_key_pair_configured() -> None:
    storage = S3Storage(
        Settings(
            s3_bucket="passit-media",
            cloudfront_domain="d111111abcdef8.cloudfront.net",
            cloudfront_key_pair_id="KIDEXAMPLE",
            cloudfront_private_key=_rsa_private_key_pem(),
        )
    )
    url = urlparse(storage.view_url("media/listing/u/k.jpg"))
    params = parse_qs(url.query)
    assert url.hostname == "d111111abcdef8.cloudfront.net"
    assert params["Key-Pair-Id"] == ["KIDEXAMPLE"]
    assert "Signature" in params and "Expires" in params


def test_cloudfront_view_url_without_key_pair_stays_public() -> None:
    storage = S3Storage(
        Settings(s3_bucket="passit-media", cloudfront_domain="d111111abcdef8.cloudfront.net")
    )
    assert storage.view_url("media/listing/u/k.jpg") == (
        "https://d111111abcdef8.cloudfront.net/media/listing/u/k.jpg"
    )
