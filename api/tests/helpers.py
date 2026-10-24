from datetime import date, timedelta
from typing import Any

import httpx

from tests.conftest import Actor

SOON = date.today() + timedelta(days=10)


def days(offset: int) -> str:
    return (SOON + timedelta(days=offset)).isoformat()


async def upload(client: httpx.AsyncClient, user: Actor, stage: str) -> str:
    """Presign and upload a tiny JPEG through the local storage stand-in; return the key."""
    presign = await client.post(
        "/media/presign", json={"stage": stage, "content_type": "image/jpeg"}, headers=user.headers
    )
    assert presign.status_code == 200, presign.text
    body = presign.json()
    put = await client.put(body["upload_url"], content=b"\xff\xd8\xff\xd9", headers=body["headers"])
    assert put.status_code == 200, put.text
    return body["key"]


async def create_listing(client: httpx.AsyncClient, user: Actor, **overrides: Any) -> dict:
    payload = {
        "title": "4-person camping tent",
        "category": "Outdoor",
        "condition": "Good",
        "price_day": "12.00",
        "price_week": "50.00",
        "deposit": "80.00",
        "mrt_station": "Clementi",
        **overrides,
    }
    response = await client.post("/listings", json=payload, headers=user.headers)
    assert response.status_code == 201, response.text
    return response.json()


async def book(
    client: httpx.AsyncClient,
    user: Actor,
    listing_id: str,
    start: int = 0,
    end: int = 2,
    duration_type: str = "day",
) -> httpx.Response:
    return await client.post(
        "/bookings",
        json={
            "listing_id": listing_id,
            "start_date": days(start),
            "end_date": days(end),
            "duration_type": duration_type,
        },
        headers=user.headers,
    )


async def checklist(
    client: httpx.AsyncClient, user: Actor, booking_id: str, stage: str
) -> httpx.Response:
    key = await upload(client, user, stage)
    path = "handover" if stage == "handover" else "return"
    return await client.post(
        f"/bookings/{booking_id}/{path}",
        json={"items": [{"label": "No scratches", "checked": True}], "media_keys": [key]},
        headers=user.headers,
    )
