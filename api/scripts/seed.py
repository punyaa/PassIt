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
import random
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import func, select, text

from app.auth.dependencies import issue_access_token
from app.auth.passwords import hash_password
from app.catalogue.mrt_stations import STATIONS
from app.core.db import get_sessionmaker
from app.models import Listing, User
from scripts.inprocess import api_client, upload_placeholder

NAMES = [
    "Aisha Rahman", "Ben Tan", "Chloe Lim", "Daniel Ng", "Elena Koh", "Farhan Ismail",
    "Grace Wong", "Hari Kumar", "Isabel Chua", "Jun Wei Lee", "Kavya Menon", "Liam Goh",
    "Mei Ling Teo", "Nur Aisyah", "Oliver Sim", "Priya Nair", "Qi Hui Ong", "Ravi Pillai",
    "Sofia Yeo", "Tom Chan",
]  # fmt: skip

# title, category, condition, day, week (or None), month (or None), deposit
ITEMS = [
    ("4-person camping tent", "Outdoor", "Good", 12, 50, 150, 80),
    ("Hiking backpack 65L", "Outdoor", "Like new", 8, 35, None, 60),
    ("Portable camping stove", "Outdoor", "Good", 6, 25, None, 40),
    ("Snorkelling set", "Outdoor", "Fair", 5, 20, None, 30),
    ("Kayak with paddles", "Outdoor", "Good", 35, 150, None, 300),
    ("Folding picnic table", "Outdoor", "Good", 7, 30, 80, 40),
    ("Party speaker with mic", "Events", "Like new", 25, 100, None, 150),
    ("Fairy lights 20m", "Events", "Good", 5, 20, None, 20),
    ("Chafing dish set", "Events", "Good", 15, 60, None, 60),
    ("Popcorn machine", "Events", "Fair", 18, 70, None, 80),
    ("Photo booth backdrop", "Events", "Good", 12, 45, None, 50),
    ("Folding chairs (10)", "Events", "Good", 20, 80, 220, 100),
    ("Cordless drill set", "Tools", "Good", 9, 35, 100, 70),
    ("Pressure washer", "Tools", "Like new", 22, 90, None, 150),
    ("Ladder 3m", "Tools", "Good", 8, 30, 90, 50),
    ("Stud finder and laser level", "Tools", "Good", 6, 24, None, 40),
    ("Carpet cleaner", "Tools", "Fair", 20, 80, None, 120),
    ("Sewing machine", "Tools", "Good", 12, 48, 140, 120),
    ("Baby stroller", "Baby & kids", "Good", 10, 40, 120, 100),
    ("Travel cot", "Baby & kids", "Like new", 8, 32, 90, 60),
    ("Car seat (0-4 years)", "Baby & kids", "Good", 9, 36, 100, 90),
    ("Kids bicycle 16 inch", "Baby & kids", "Fair", 6, 24, 70, 50),
    ("Baby carrier", "Baby & kids", "Good", 5, 20, 60, 50),
    ("Ride-on toy car", "Baby & kids", "Good", 10, 40, None, 80),
    ("Fujifilm camera kit", "Electronics", "Like new", 28, 120, None, 400),
    ("Portable projector", "Electronics", "Good", 22, 90, 250, 250),
    ("Nintendo Switch with games", "Electronics", "Good", 15, 60, 170, 250),
    ("DJI drone", "Electronics", "Like new", 45, 190, None, 600),
    ("GoPro action camera", "Electronics", "Good", 18, 75, 210, 250),
    ("VR headset", "Electronics", "Good", 25, 100, None, 350),
    ("Stand mixer", "Home", "Good", 12, 48, None, 150),
    ("Air fryer XL", "Home", "Like new", 8, 30, 85, 80),
    ("Dehumidifier", "Home", "Good", 7, 28, 80, 90),
    ("Steam iron station", "Home", "Good", 6, 24, None, 60),
    ("Raclette grill", "Home", "Like new", 10, 40, None, 70),
    ("Bread maker", "Home", "Good", 8, 30, None, 70),
    ("Electric scooter", "Mobility", "Good", 20, 85, 240, 300),
    ("Foldable bicycle", "Mobility", "Good", 15, 60, 170, 250),
    ("Roof box for car", "Mobility", "Fair", 18, 70, None, 150),
    ("Luggage set (3 pieces)", "Travel", "Good", 10, 40, 110, 120),
]  # fmt: skip

# Final state for each of the 15 bookings.
BOOKING_PLAN = (
    ["confirmed"] * 3
    + ["handed_over"] * 3
    + ["returned"] * 2
    + ["settled"] * 3
    + ["damaged"] * 2
    + ["cancelled"] * 2
)


async def reset() -> None:
    async with get_sessionmaker()() as db:
        await db.execute(
            text(
                "TRUNCATE reviews, checklists, media, ledger_entries, bookings, "
                "availability, listings, users CASCADE"
            )
        )
        await db.commit()


DEMO_PASSWORD = "passit-demo-2026"


async def create_users() -> list[UUID]:
    password_hash = hash_password(DEMO_PASSWORD)  # one hash for all 20 accounts
    async with get_sessionmaker()() as db:
        users = [
            User(
                email=f"seed-{index:02d}@passit.demo",
                password_hash=password_hash,
                display_name=name,
            )
            for index, name in enumerate(NAMES, start=1)
        ]
        db.add_all(users)
        await db.commit()
        return [user.id for user in users]


def auth(user_id: UUID) -> dict[str, str]:
    return {"authorization": f"Bearer {issue_access_token(user_id, timedelta(days=30))}"}


async def run(rng: random.Random) -> None:
    user_ids = await create_users()
    async with api_client() as client:
        listings = []
        for index, (title, category, condition, day, week, month, deposit) in enumerate(ITEMS):
            owner = user_ids[index % len(user_ids)]  # two listings per user
            station = rng.choice(STATIONS)
            payload = {
                "title": title,
                "description": f"{condition} {title.lower()}, available for pickup near "
                f"{station.name} MRT.",
                "category": category,
                "condition": condition,
                "price_day": str(day),
                "price_week": str(week) if week else None,
                "price_month": str(month) if month else None,
                "deposit": str(deposit),
                "mrt_station": station.name,
                # No listing photos: cards fall back to a category illustration. Seeded
                # handovers and returns still upload placeholder evidence.
            }
            response = await client.post("/listings", json=payload, headers=auth(owner))
            response.raise_for_status()
            listings.append((response.json(), owner))

        for index, final_state in enumerate(BOOKING_PLAN):
            listing, owner = listings[index * 2 + 1]
            borrower = rng.choice([u for u in user_ids if u != owner])
            start = date.today() + timedelta(days=rng.randint(3, 40))
            response = await client.post(
                "/bookings",
                json={
                    "listing_id": listing["id"],
                    "start_date": start.isoformat(),
                    "end_date": (start + timedelta(days=rng.randint(1, 5))).isoformat(),
                    "duration_type": "day",
                },
                headers=auth(borrower),
            )
            response.raise_for_status()
            booking_id = response.json()["id"]
            await advance(client, booking_id, final_state, auth(owner), auth(borrower), rng)

    async with get_sessionmaker()() as db:
        listing_count = await db.scalar(select(func.count()).select_from(Listing))
    print(f"Seeded {len(user_ids)} users, {listing_count} listings, {len(BOOKING_PLAN)} bookings.")
    print(f"Demo logins: seed-01@passit.demo ... seed-20@passit.demo, password {DEMO_PASSWORD}")
    print("Session tokens (valid 30 days) for the demo:")
    for user_id, name in list(zip(user_ids, NAMES, strict=True))[:3]:
        print(f"  {name:<14} {auth(user_id)['authorization']}")


async def advance(client, booking_id, final_state, lender, borrower, rng) -> None:  # noqa: ANN001
    async def checklist(path: str, headers: dict, stage: str) -> None:
        key = await upload_placeholder(client, headers, stage)
        items = [
            {"label": "Item clean and complete", "checked": True},
            {"label": "No visible damage", "checked": stage == "handover" or rng.random() > 0.3},
        ]
        response = await client.post(
            f"/bookings/{booking_id}/{path}",
            json={"items": items, "media_keys": [key]},
            headers=headers,
        )
        response.raise_for_status()

    async def post(path: str, headers: dict, body: dict | None = None) -> None:
        response = await client.post(f"/bookings/{booking_id}/{path}", json=body, headers=headers)
        response.raise_for_status()

    if final_state == "cancelled":
        await post("cancel", borrower)
        return
    if final_state == "confirmed":
        return
    await checklist("handover", lender, "handover")
    if final_state == "handed_over":
        return
    await checklist("return", borrower, "return")
    if final_state == "returned":
        return
    if final_state == "damaged":
        severity = rng.choice(["minor", "moderate"])
        await post("damage", lender, {"severity": severity, "notes": "Scuffs on the casing"})
    else:
        await post("settle", lender)
    for author in (borrower, lender):
        review = {"booking_id": booking_id, "rating": rng.randint(4, 5), "comment": "Smooth rental"}
        response = await client.post("/reviews", json=review, headers=author)
        response.raise_for_status()


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
    await run(random.Random(5224))


if __name__ == "__main__":
    asyncio.run(main())
