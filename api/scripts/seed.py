"""Deterministic demo data (B3): 20 users, 40 listings, 15 bookings across the lifecycle.

    uv run --directory api python -m scripts.seed --reset
    docker compose exec api python -m scripts.seed --reset

Bookings are driven through the real API in-process, so every ledger entry, checklist and
state transition is produced by the same code the app uses. Seed users sign in as
`seed-01@passit.demo` to `seed-20@passit.demo` with the password below, and the script also
prints session tokens for load tests.
"""

import argparse
import asyncio
from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID

import httpx
from sqlalchemy import func, select, text, update

from app.auth.dependencies import issue_access_token
from app.auth.passwords import hash_password
from app.core.config import get_settings
from app.core.db import get_sessionmaker
from app.models import (
    Booking,
    Checklist,
    LedgerEntry,
    Listing,
    Media,
    Review,
    User,
    inclusive_range,
)
from app.transactions.release import handle_release
from scripts.demo_data import BOOKING_PLAN, DEMO_ROOT, ITEMS, PEOPLE, DemoItem, DemoScenario
from scripts.inprocess import api_client, upload_bytes

DEMO_PASSWORD = "passit-demo-2026"


async def reset() -> None:
    async with get_sessionmaker()() as db:
        await db.execute(
            text(
                "TRUNCATE meetup_events, meetups, saved_listings, reviews, checklists, media, "
                "ledger_entries, bookings, availability, listings, users CASCADE"
            )
        )
        await db.commit()


async def create_users(today: date) -> list[UUID]:
    password_hash = hash_password(DEMO_PASSWORD)  # one hash for all 20 accounts
    async with get_sessionmaker()() as db:
        users = [
            User(
                email=f"seed-{index:02d}@passit.demo",
                password_hash=password_hash,
                display_name=person["name"],
                bio=person["bio"],
                created_at=datetime.combine(today, time(9), UTC) - timedelta(days=180 + index * 12),
            )
            for index, person in enumerate(PEOPLE, start=1)
        ]
        db.add_all(users)
        await db.commit()
        return [user.id for user in users]


def auth(user_id: UUID) -> dict[str, str]:
    return {"authorization": f"Bearer {issue_access_token(user_id, timedelta(days=30))}"}


async def upload_item_photo(
    client: httpx.AsyncClient, user_id: UUID, stage: str, item: DemoItem, position: int
) -> str:
    photo = item["photos"][min(position, len(item["photos"]) - 1)]
    data = (DEMO_ROOT / "media" / photo["file"]).read_bytes()
    return await upload_bytes(client, auth(user_id), stage, data, "image/jpeg")


async def run() -> None:
    today = date.today()
    user_ids = await create_users(today)
    listings: dict[str, tuple[UUID, UUID, DemoItem]] = {}
    async with api_client() as client:
        for index, item in enumerate(ITEMS):
            owner = user_ids[item["owner"]]  # two related listings per user
            photos = [
                await upload_item_photo(client, owner, "listing", item, position)
                for position in range(len(item["photos"]))
            ]
            payload = {
                key: item[key]
                for key in (
                    "title",
                    "description",
                    "category",
                    "condition",
                    "price_day",
                    "price_week",
                    "price_month",
                    "deposit",
                    "mrt_station",
                )
            }
            payload["availability"] = [
                {
                    "start_date": (today - timedelta(days=60)).isoformat(),
                    "end_date": (today + timedelta(days=365)).isoformat(),
                }
            ]
            # Bundled listing photos use the real upload flow. Seeded handovers and
            # returns upload separate copies as condition evidence.
            payload["photo_keys"] = photos
            response = await client.post("/listings", json=payload, headers=auth(owner))
            response.raise_for_status()
            listing_id = UUID(response.json()["id"])
            listings[item["slug"]] = listing_id, owner, item
            async with get_sessionmaker()() as db:
                created = datetime.combine(today, time(10), UTC) - timedelta(days=45 + index)
                await db.execute(
                    update(Listing).where(Listing.id == listing_id).values(created_at=created)
                )
                await db.execute(
                    update(Media).where(Media.listing_id == listing_id).values(created_at=created)
                )
                await db.commit()

        for scenario in BOOKING_PLAN:
            listing_id, owner, item = listings[scenario["item"]]
            borrower = user_ids[scenario["borrower"]]
            # Production rejects past bookings. Build a real rental of the same duration
            # first, then date the completed fixture consistently in historical_time().
            start = today + timedelta(days=max(0, scenario["start"]))
            response = await client.post(
                "/bookings",
                json={
                    "listing_id": str(listing_id),
                    "start_date": start.isoformat(),
                    "end_date": (
                        start + timedelta(days=scenario["end"] - scenario["start"])
                    ).isoformat(),
                    "duration_type": "day",
                },
                headers=auth(borrower),
            )
            response.raise_for_status()
            booking_id = UUID(response.json()["id"])
            await advance(client, booking_id, scenario, item, owner, borrower)
            await historical_time(booking_id, scenario, today)

        for user_index, slugs in (
            (0, ["projector", "mixer", "luggage"]),
            (1, ["tent", "speaker", "vr"]),
            (2, ["backpack", "sewing"]),
        ):
            for slug in slugs:
                response = await client.put(
                    f"/saved-listings/{listings[slug][0]}", headers=auth(user_ids[user_index])
                )
                response.raise_for_status()
        # Pause after scenarios are created, keeping the real public-availability rule.
        for item in ITEMS:
            if item["status"] == "paused":
                response = await client.patch(
                    f"/listings/{listings[item['slug']][0]}",
                    json={"status": "paused"},
                    headers=auth(user_ids[item["owner"]]),
                )
                response.raise_for_status()

    async with get_sessionmaker()() as db:
        listing_count = await db.scalar(select(func.count()).select_from(Listing))
    print(f"Seeded {len(user_ids)} users, {listing_count} listings, {len(BOOKING_PLAN)} bookings.")
    print(f"Demo logins: seed-01@passit.demo ... seed-20@passit.demo, password {DEMO_PASSWORD}")
    print("Session tokens (valid 30 days) for the demo:")
    for user_id, person in list(zip(user_ids, PEOPLE, strict=True))[:3]:
        print(f"  {person['name']:<14} {auth(user_id)['authorization']}")


async def advance(
    client: httpx.AsyncClient,
    booking_id: UUID,
    scenario: DemoScenario,
    item: DemoItem,
    owner: UUID,
    borrower: UUID,
) -> None:
    final_state = scenario["state"]

    async def checklist(path: str, user_id: UUID, stage: str) -> None:
        key = await upload_item_photo(client, user_id, stage, item, 0 if stage == "handover" else 1)
        items = [
            {"label": item["check"], "checked": True},
            {"label": "Condition and existing wear checked together", "checked": True},
        ]
        response = await client.post(
            f"/bookings/{booking_id}/{path}",
            json={"items": items, "media_keys": [key]},
            headers=auth(user_id),
        )
        response.raise_for_status()

    async def post(path: str, user_id: UUID, body: dict[str, str] | None) -> None:
        response = await client.post(
            f"/bookings/{booking_id}/{path}", json=body, headers=auth(user_id)
        )
        response.raise_for_status()

    if final_state == "cancelled":
        await post("cancel", borrower, None)
        return
    if final_state == "confirmed":
        return
    await checklist("handover", owner, "handover")
    if final_state == "handed_over":
        return
    await checklist("return", borrower, "return")
    if final_state == "returned":
        return
    if final_state == "damaged":
        await post("damage", owner, {"severity": scenario["severity"], "notes": scenario["damage"]})
    else:
        await post("settle", owner, None)
    for author, comment in ((borrower, scenario["review"]), (owner, scenario["lender_review"])):
        review = {
            "booking_id": str(booking_id),
            "rating": 4 if final_state == "damaged" else 5,
            "comment": comment,
        }
        response = await client.post("/reviews", json=review, headers=auth(author))
        response.raise_for_status()


async def historical_time(booking_id: UUID, scenario: DemoScenario, today: date) -> None:
    """Backdate this demo fixture only; never change application validation or money amounts."""
    start = today + timedelta(days=scenario["start"])
    end = today + timedelta(days=scenario["end"])
    created = datetime.combine(
        min(start - timedelta(days=5), today - timedelta(days=2)), time(9), UTC
    )
    handover = datetime.combine(start, time(10), UTC)
    returned = datetime.combine(end, time(18), UTC)
    settled = returned + timedelta(hours=1)
    cancelled = created + timedelta(hours=2)
    async with get_sessionmaker()() as db:
        booking = await db.get(Booking, booking_id)
        booking.period = inclusive_range(start, end)
        booking.created_at = created
        if booking.handed_over_at is not None:
            booking.handed_over_at = handover
            booking.fee_release_at = handover + timedelta(minutes=get_settings().fee_hold_minutes)
        if booking.returned_at is not None:
            booking.returned_at = returned
        if booking.settled_at is not None:
            booking.settled_at = settled
        if booking.cancelled_at is not None:
            booking.cancelled_at = cancelled
        for row in await db.scalars(select(Checklist).where(Checklist.booking_id == booking_id)):
            row.signed_at = handover if row.stage == "handover" else returned
        for row in await db.scalars(select(Media).where(Media.booking_id == booking_id)):
            row.created_at = handover if row.stage == "handover" else returned
        for row in await db.scalars(select(Review).where(Review.booking_id == booking_id)):
            row.created_at = settled + timedelta(hours=1)
        for row in await db.scalars(
            select(LedgerEntry).where(LedgerEntry.booking_id == booking_id)
        ):
            if row.entry_type in ("refund_deposit", "damage_payout"):
                row.created_at = settled
            elif booking.state == "cancelled" and (
                (row.account == "borrower" and row.amount > 0)
                or (row.account == "platform_hold" and row.amount < 0)
            ):
                row.created_at = cancelled
            else:
                row.created_at = created
        await db.commit()
    # Use the normal idempotent release service for fees whose historical hold has ended.
    await handle_release(booking_id)
    async with get_sessionmaker()() as db:
        booking = await db.get(Booking, booking_id)
        await db.execute(
            update(LedgerEntry)
            .where(LedgerEntry.booking_id == booking_id, LedgerEntry.entry_type == "release_fee")
            .values(created_at=booking.fee_release_at)
        )
        await db.commit()


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reset", action="store_true", help="wipe all PassIt data first")
    args = parser.parse_args()
    if args.reset:
        await reset()
    else:
        async with get_sessionmaker()() as db:
            if await db.scalar(select(func.count()).select_from(User)):
                raise SystemExit("Database is not empty. Re-run with --reset to replace it.")
    await run()


if __name__ == "__main__":
    asyncio.run(main())
