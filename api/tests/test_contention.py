"""B1 contention harness: concurrent requests for the same dates must yield exactly one
booking. Week 1 spike runs 20 connections; the Week 2 gate runs 50."""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from app.transactions.release import handle_release
from tests.helpers import book, checklist, create_listing

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize("concurrency", [20, 50])
async def test_concurrent_bookings_for_same_dates_produce_one_winner(
    client, make_user, sql, concurrency
):
    lender = make_user("Lena")
    listing = await create_listing(client, lender)
    borrowers = [make_user(f"Borrower{i}") for i in range(concurrency)]

    responses = await asyncio.gather(
        *(book(client, borrower, listing["id"], 0, 6, "week") for borrower in borrowers)
    )

    statuses = sorted(response.status_code for response in responses)
    assert statuses.count(201) == 1, statuses
    assert statuses.count(409) == concurrency - 1, statuses
    rows = sql(
        "SELECT count(*) FROM bookings WHERE listing_id = %s AND state = 'confirmed'",
        listing["id"],
    )
    assert rows[0][0] == 1
    # Only the winner holds funds: no orphan ledger entries from the losers.
    held = sql("SELECT count(DISTINCT booking_id) FROM ledger_entries")
    assert held[0][0] == 1


async def test_overlapping_but_not_identical_ranges_also_conflict(client, make_user):
    lender = make_user("Lena")
    listing = await create_listing(client, lender)
    a, b = make_user("Ann"), make_user("Bob")
    responses = await asyncio.gather(
        book(client, a, listing["id"], 0, 3), book(client, b, listing["id"], 3, 5)
    )
    assert sorted(r.status_code for r in responses) == [201, 409]


async def test_duplicate_release_deliveries_release_once(client, make_user, sql):
    lender, borrower = make_user("Lena"), make_user("Ben")
    listing = await create_listing(client, lender)
    booking = (await book(client, borrower, listing["id"])).json()
    await checklist(client, lender, booking["id"], "handover")

    later = datetime.now(UTC) + timedelta(days=8)
    results = await asyncio.gather(*(handle_release(booking["id"], later) for _ in range(10)))

    assert sorted(r["status"] for r in results).count("released") == 1
    released = sql(
        "SELECT count(*) FROM ledger_entries WHERE booking_id = %s AND entry_type = 'release_fee'",
        booking["id"],
    )
    assert released[0][0] == 2  # one balanced pair
    payouts = sql(
        "SELECT count(*) FROM payment_operations po JOIN payments p ON p.id = po.payment_id "
        "WHERE p.booking_id = %s AND po.operation = 'payout'",
        booking["id"],
    )
    assert payouts[0][0] == 1


async def test_deadlock_between_overlapping_requests_is_a_conflict_not_a_500(
    client, make_user, monkeypatch
):
    """PostgreSQL aborts one of two concurrently overlapping inserts with a deadlock error.
    That request lost the dates, so it must answer 409 like any other conflict."""
    from sqlalchemy.exc import OperationalError

    from app.transactions import service as ledger_service

    class Deadlock(Exception):
        sqlstate = "40P01"

    async def deadlocked(*_args, **_kwargs):
        raise OperationalError("INSERT", {}, Deadlock())

    lender, borrower = make_user("Lena"), make_user("Ben")
    listing = await create_listing(client, lender)
    monkeypatch.setattr(ledger_service, "hold_funds", deadlocked)

    response = await book(client, borrower, listing["id"], 0, 2)

    assert response.status_code == 409, response.text
    assert response.json()["detail"] == "Those dates are already booked"
