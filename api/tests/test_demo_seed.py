"""The demo must reset into a coherent, offline, usable application state."""

from collections import Counter
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from PIL import Image
from sqlalchemy import func, select

from app.auth.dependencies import issue_access_token
from app.core.config import get_settings
from app.core.db import get_sessionmaker
from app.models import Booking, Checklist, LedgerEntry, Listing, Media, Review, SavedListing, User
from scripts.demo_data import BOOKING_PLAN, DEMO_ROOT, ITEMS, PEOPLE
from scripts.seed import reset, run


def test_demo_assets_and_scenarios_are_self_contained():
    assert len(ITEMS) == 40 and len(PEOPLE) == 20 and len(BOOKING_PLAN) == 15
    assert len({item["slug"] for item in ITEMS}) == 40
    assert Counter(item["owner"] for item in ITEMS) == {i: 2 for i in range(20)}
    assert len({person["bio"] for person in PEOPLE}) == 20
    assert sum(len(item["photos"]) > 1 for item in ITEMS) == 8
    for item in ITEMS:
        assert item["source_page"].startswith("https://")
        assert len(item["description"]) > 180
        for photo in item["photos"]:
            assert photo["source_url"].startswith("https://")
            with Image.open(DEMO_ROOT / "media" / photo["file"]) as image:
                assert image.format == "JPEG"
                assert 100 < min(image.size) and max(image.size) <= 1280
                assert not image.getexif()
    items = {item["slug"]: item for item in ITEMS}
    for scenario in BOOKING_PLAN:
        assert scenario["borrower"] != items[scenario["item"]]["owner"]
        assert scenario["end"] >= scenario["start"]
        if scenario["state"] in ("returned", "settled", "damaged"):
            assert scenario["end"] < 0
        if scenario["state"] == "confirmed":
            assert scenario["start"] > 0
        if scenario["state"] == "handed_over":
            assert scenario["start"] < 0 <= scenario["end"]


@pytest.mark.anyio
async def test_demo_reset_preserves_lifecycle_and_populates_new_screens(
    client, monkeypatch, capsys
):
    monkeypatch.setattr(get_settings(), "fee_hold_minutes", 7 * 24 * 60)
    await run()
    capsys.readouterr()  # Demo tokens are an operator convenience, not test output.
    today, now = date.today(), datetime.now(UTC)
    async with get_sessionmaker()() as db:
        assert await db.scalar(select(func.count()).select_from(User)) == 20
        assert await db.scalar(select(func.count()).select_from(Listing)) == 40
        assert await db.scalar(select(func.count()).select_from(Booking)) == 15
        assert await db.scalar(select(func.count()).select_from(SavedListing)) == 8
        users = list(await db.scalars(select(User)))
        assert all(user.bio and user.created_at < now for user in users)
        aisha = next(user for user in users if user.email == "seed-01@passit.demo")
        headers = {"authorization": f"Bearer {issue_access_token(aisha.id)}"}
        listings = list(await db.scalars(select(Listing)))
        assert Counter(item.status for item in listings) == {"active": 38, "paused": 2}
        listing_media = list(await db.scalars(select(Media).where(Media.stage == "listing")))
        assert len(listing_media) == sum(len(item["photos"]) for item in ITEMS)
        bookings = list(await db.scalars(select(Booking)))
        assert Counter(booking.state for booking in bookings) == {
            "confirmed": 3,
            "handed_over": 3,
            "returned": 2,
            "settled": 5,
            "cancelled": 2,
        }
        for booking in bookings:
            assert booking.created_at <= now
            if booking.state == "confirmed":
                assert booking.start_date > today
            elif booking.state == "handed_over":
                assert booking.start_date < today <= booking.end_date
            elif booking.state in ("returned", "settled"):
                assert booking.end_date < today
            if booking.handed_over_at:
                assert booking.created_at < booking.handed_over_at <= now
                assert booking.handed_over_at.date() == booking.start_date
            if booking.returned_at:
                assert booking.handed_over_at < booking.returned_at <= now
                assert booking.returned_at.date() == booking.end_date
            if booking.settled_at:
                assert booking.returned_at < booking.settled_at <= now
            for checklist in await db.scalars(
                select(Checklist).where(Checklist.booking_id == booking.id)
            ):
                assert checklist.signed_at == (
                    booking.handed_over_at if checklist.stage == "handover" else booking.returned_at
                )
            entries = list(
                await db.scalars(select(LedgerEntry).where(LedgerEntry.booking_id == booking.id))
            )
            assert sum(entry.amount for entry in entries) == Decimal(0)
            assert all(booking.created_at <= entry.created_at <= now for entry in entries)
            if booking.state == "settled":
                assert any(entry.entry_type == "release_fee" for entry in entries)
        reviews = list(await db.scalars(select(Review)))
        assert len(reviews) == len({review.comment for review in reviews}) == 10
        assert all(review.created_at < now for review in reviews)

    public = (await client.get("/listings", params={"limit": 50})).json()
    assert len(public) == 38 and all(item["photo_urls"] for item in public)
    assert all(len(item["thumbnail_urls"]) == len(item["photo_urls"]) for item in public)
    saved = (await client.get("/saved-listings", headers=headers)).json()
    assert len(saved) == 3
    rentals = (await client.get("/bookings", params={"role": "all"}, headers=headers)).json()
    assert {rental["viewer_role"] for rental in rentals} == {"borrower", "lender"}
    assert any(rental["state"] == "confirmed" for rental in rentals)
    assert any(rental["state"] == "handed_over" for rental in rentals)
    assert any(rental["state"] == "returned" for rental in rentals)
    assert any(rental["state"] == "settled" for rental in rentals)
    await reset()
    async with get_sessionmaker()() as db:
        assert await db.scalar(select(func.count()).select_from(User)) == 0
        assert await db.scalar(select(func.count()).select_from(SavedListing)) == 0
