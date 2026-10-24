"""End-to-end rental journey through the HTTP API against real PostgreSQL."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.transactions.release import handle_release, release_due_fees
from tests.helpers import book, checklist, create_listing, days, upload

pytestmark = pytest.mark.anyio


def ledger_sum(sql, booking_id: str, account: str | None = None) -> Decimal:
    query = "SELECT COALESCE(SUM(amount), 0) FROM ledger_entries WHERE booking_id = %s"
    params: tuple = (booking_id,)
    if account:
        query += " AND account = %s"
        params += (account,)
    return sql(query, *params)[0][0]


async def test_full_journey_book_handover_return_settle_review(client, make_user, sql):
    lender, borrower = make_user("Lena"), make_user("Ben")
    photo = await upload(client, lender, "listing")
    listing = await create_listing(client, lender, photo_keys=[photo])
    assert listing["mrt_station"] == "Clementi" and listing["planning_area"] == "Clementi"
    assert len(listing["photo_urls"]) == 1

    created = await book(client, borrower, listing["id"], 0, 2)
    assert created.status_code == 201, created.text
    booking = created.json()
    assert booking["state"] == "confirmed"
    assert booking["fee"] == "36.00"  # 3 inclusive days x 12.00
    assert booking["available_actions"] == ["handover", "cancel"]
    assert ledger_sum(sql, booking["id"]) == 0
    assert ledger_sum(sql, booking["id"], "platform_hold") == Decimal("116.00")

    handed = await checklist(client, lender, booking["id"], "handover")
    assert handed.status_code == 200, handed.text
    assert handed.json()["state"] == "handed_over"
    assert handed.json()["fee_release_at"] is not None

    returned = await checklist(client, borrower, booking["id"], "return")
    assert returned.json()["state"] == "returned"
    assert returned.json()["available_actions"] == ["review"]  # borrower cannot settle

    settled = await client.post(f"/bookings/{booking['id']}/settle", headers=lender.headers)
    assert settled.status_code == 200, settled.text
    assert settled.json()["state"] == "settled"

    evidence = await client.get(f"/bookings/{booking['id']}/checklists", headers=borrower.headers)
    assert [c["stage"] for c in evidence.json()] == ["handover", "return"]
    assert all(len(c["media_urls"]) == 1 for c in evidence.json())

    # Fee is still held until the hold period ends, then released exactly once.
    assert (await handle_release(booking["id"]))["status"] == "not_due"
    later = datetime.now(UTC) + timedelta(days=8)
    assert [r["status"] for r in await release_due_fees(later)] == ["released"]
    assert (await handle_release(booking["id"], later))["status"] == "already_released"
    assert ledger_sum(sql, booking["id"]) == 0
    assert ledger_sum(sql, booking["id"], "platform_hold") == 0
    assert ledger_sum(sql, booking["id"], "lender") == Decimal("36.00")
    assert ledger_sum(sql, booking["id"], "borrower") == Decimal("-36.00")

    for author in (borrower, lender):
        review = await client.post(
            "/reviews", json={"booking_id": booking["id"], "rating": 5}, headers=author.headers
        )
        assert review.status_code == 201, review.text
    duplicate = await client.post(
        "/reviews", json={"booking_id": booking["id"], "rating": 1}, headers=lender.headers
    )
    assert duplicate.status_code == 409
    detail = (await client.get(f"/listings/{listing['id']}")).json()
    assert detail["owner_rating"] == 5.0 and detail["owner_review_count"] == 1

    lender_dash = (await client.get("/dashboard?role=lender", headers=lender.headers)).json()
    assert lender_dash["earnings"] == "36.00" and lender_dash["completed_rentals"] == 1
    assert lender_dash["pending_release"] == "0.00"
    borrower_dash = (await client.get("/dashboard", headers=borrower.headers)).json()
    assert borrower_dash["total_spent"] == "36.00"
    assert borrower_dash["savings"] == "44.00"  # deposit 80 - fee 36
    assert borrower_dash["deposits_held"] == "0.00"


async def test_damage_report_splits_deposit_by_tier(client, make_user, sql):
    lender, borrower = make_user("Lena"), make_user("Ben")
    listing = await create_listing(client, lender, deposit="80.00")
    booking = (await book(client, borrower, listing["id"])).json()
    await checklist(client, borrower, booking["id"], "handover")
    await checklist(client, lender, booking["id"], "return")

    damage = await client.post(
        f"/bookings/{booking['id']}/damage",
        json={"severity": "moderate", "notes": "Torn flysheet"},
        headers=lender.headers,
    )
    assert damage.status_code == 200, damage.text
    assert damage.json()["damage_severity"] == "moderate"
    payouts = sql(
        "SELECT account, entry_type, amount FROM ledger_entries "
        "WHERE booking_id = %s AND entry_type IN ('damage_payout', 'refund_deposit') "
        "ORDER BY entry_type::text, account",
        booking["id"],
    )
    assert payouts == [
        ("lender", "damage_payout", Decimal("32.00")),
        ("platform_hold", "damage_payout", Decimal("-32.00")),
        ("borrower", "refund_deposit", Decimal("48.00")),
        ("platform_hold", "refund_deposit", Decimal("-48.00")),
    ]
    assert ledger_sum(sql, booking["id"]) == 0
    dash = (await client.get("/dashboard", headers=borrower.headers)).json()
    assert dash["total_spent"] == "68.00"  # 36 fee + 32 damage


async def test_cancel_refunds_holds_and_frees_dates(client, make_user, sql):
    lender, first, second = make_user("Lena"), make_user("Ben"), make_user("Cara")
    listing = await create_listing(client, lender)
    booking = (await book(client, first, listing["id"])).json()
    assert (await book(client, second, listing["id"])).status_code == 409

    cancelled = await client.post(f"/bookings/{booking['id']}/cancel", headers=first.headers)
    assert cancelled.json()["state"] == "cancelled"
    for account in ("borrower", "platform_hold", "lender"):
        assert ledger_sum(sql, booking["id"], account) == 0

    assert (await book(client, second, listing["id"])).status_code == 201
    again = await client.post(f"/bookings/{booking['id']}/cancel", headers=first.headers)
    assert again.status_code == 409


async def test_booking_rules(client, make_user):
    lender, borrower, stranger = make_user("Lena"), make_user("Ben"), make_user("Sam")
    listing = await create_listing(
        client,
        lender,
        availability=[{"start_date": days(0), "end_date": days(5)}],
    )
    assert (await book(client, lender, listing["id"])).status_code == 400  # own item
    assert (await book(client, borrower, listing["id"], 4, 8)).status_code == 409  # outside
    no_month = await book(client, borrower, listing["id"], 0, 2, "month")
    assert no_month.status_code == 400

    booking = (await book(client, borrower, listing["id"], 0, 1)).json()
    hidden = await client.get(f"/bookings/{booking['id']}", headers=stranger.headers)
    assert hidden.status_code == 404
    early_return = await checklist(client, borrower, booking["id"], "return")
    assert early_return.status_code == 409
    no_photos = await client.post(
        f"/bookings/{booking['id']}/handover",
        json={"items": [{"label": "ok", "checked": True}], "media_keys": []},
        headers=borrower.headers,
    )
    assert no_photos.status_code == 422
    stolen_key = await upload(client, stranger, "handover")
    foreign = await client.post(
        f"/bookings/{booking['id']}/handover",
        json={"items": [{"label": "ok", "checked": True}], "media_keys": [stolen_key]},
        headers=borrower.headers,
    )
    assert foreign.status_code == 400

    availability = await client.get(
        f"/listings/{listing['id']}/availability", params={"from": days(0), "to": days(3)}
    )
    body = availability.json()
    assert body["available"] is False
    assert body["booked"] == [{"start_date": days(0), "end_date": days(1)}]
    free = await client.get(
        f"/listings/{listing['id']}/availability", params={"from": days(2), "to": days(5)}
    )
    assert free.json()["available"] is True

    unauthenticated = await client.post("/bookings", json={})
    assert unauthenticated.status_code in (401, 422)
    listed = await client.get("/bookings?role=lender", headers=lender.headers)
    assert [b["id"] for b in listed.json()] == [booking["id"]]
