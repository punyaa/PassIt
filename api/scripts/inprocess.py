"""Drive the API in-process, so scripts exercise the same rules as real clients."""

import base64
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx

from app.core.config import get_settings
from app.main import app


@asynccontextmanager
async def api_client() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://passit/v1", timeout=30
    ) as client:
        yield client


async def upload_placeholder(client: httpx.AsyncClient, headers: dict, stage: str) -> str:
    """Upload a 1x1 PNG through whichever storage backend is configured."""
    presign = await client.post(
        "/media/presign", json={"stage": stage, "content_type": "image/png"}, headers=headers
    )
    presign.raise_for_status()
    body = presign.json()
    url = body["upload_url"]
    local = url.startswith(get_settings().public_api_url)
    if local:  # local storage stand-in: send to the in-process app
        url = url.replace(get_settings().public_api_url, "http://passit", 1)
        response = await client.put(url, content=PLACEHOLDER_PNG, headers=body["headers"])
    else:  # real presigned S3 URL
        async with httpx.AsyncClient(timeout=30) as s3:
            response = await s3.put(url, content=PLACEHOLDER_PNG, headers=body["headers"])
    response.raise_for_status()
    return body["key"]


# A valid 1x1 PNG, so seeded photos render instead of showing a broken image.
PLACEHOLDER_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
)
