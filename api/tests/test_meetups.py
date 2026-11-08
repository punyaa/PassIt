"""Meetups: borrower and lender take turns until one accepts the other's terms."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from app.auth.dependencies import issue_access_token
from tests.helpers import book, checklist, create_listing

pytestmark = pytest.mark.anyio


def later(hours: int) -> str:
    return (datetime.now(UTC) + timedelta(hours=hours)).isoformat()


def terms(hours: int = 48, location: str = "Clementi MRT exit A", price: str = "30.00", **extra):
    return {"meet_at": later(hours), "location": location, "price": price, **extra}


async def booked(client, borrower, listing_id: str, start: int = 0, end: int = 2) -> str:
    response = await book(client, borrower, listing_id, start, end)
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def propose(client, borrower, booking_id: str, **overrides):
    return await client.post(
        "/meetups",
        json={"booking_id": booking_id, **terms(), **overrides},
        headers=borrower.headers,
    )


async def test_borrower_and_lender_negotiate_then_meeting_is_scheduled(client, make_user):
    lena, ben = make_user("Lena"), make_user("Ben")
    listing = await create_listing(client, lena)
    booking_id = await booked(client, ben, listing["id"])

    created = await propose(client, ben, booking_id, message="Could we meet after work?")
    assert created.status_code == 201, created.text
    meetup = created.json()
    assert meetup["status"] == "pending"
    assert meetup["awaiting_role"] == "lender"
    assert meetup["viewer_role"] == "borrower"
    assert meetup["available_actions"] == ["cancel"]
    assert meetup["listing_title"] == listing["title"]
    assert meetup["booking_id"] == booking_id
    assert meetup["lender_display_name"] == "Lena"

    # The lender sees the request on their side, with the borrower's message.
    inbox = (await client.get("/meetups?role=lender&status=pending", headers=lena.headers)).json()
    assert [m["id"] for m in inbox] == [meetup["id"]]
    assert inbox[0]["available_actions"] == ["accept", "counter", "decline"]
    assert inbox[0]["events"][0]["message"] == "Could we meet after work?"
    assert (await client.get("/meetups?role=borrower", headers=lena.headers)).json() == []

    # The borrower cannot accept their own offer.
    own = await client.post(f"/meetups/{meetup['id']}/accept", headers=ben.headers)
    assert own.status_code == 409

    countered = await client.post(
        f"/meetups/{meetup['id']}/counter",
        json=terms(72, "Clementi Mall lobby", "35.00", message="Saturday works better"),
        headers=lena.headers,
    )
    assert countered.status_code == 200, countered.text
    body = countered.json()
    assert body["awaiting_role"] == "borrower"
    assert body["location"] == "Clementi Mall lobby"
    assert body["price"] == "35.00"
    assert body["available_actions"] == ["cancel"]

    accepted = await client.post(
        f"/meetups/{meetup['id']}/accept", json={"message": "See you then"}, headers=ben.headers
    )
    assert accepted.status_code == 200, accepted.text
    scheduled = accepted.json()
    assert scheduled["status"] == "accepted"
    assert scheduled["awaiting_role"] is None
    assert scheduled["available_actions"] == ["cancel"]
    assert [e["kind"] for e in scheduled["events"]] == ["propose", "counter", "accept"]
    assert scheduled["events"][1]["price"] == "35.00"
    assert scheduled["events"][2]["author_display_name"] == "Ben"

    # Both sides see the scheduled meeting.
    for person in (lena, ben):
        mine = (await client.get("/meetups?status=accepted", headers=person.headers)).json()
        assert [m["id"] for m in mine] == [meetup["id"]]

    # Closed negotiations cannot be reopened by countering.
    late = await client.post(f"/meetups/{meetup['id']}/counter", json=terms(), headers=lena.headers)
    assert late.status_code == 409


async def test_proposal_rules(client, make_user, sql):
    lena, ben, otto = make_user("Lena"), make_user("Ben"), make_user("Otto")
    listing = await create_listing(client, lena)
    booking_id = await booked(client, ben, listing["id"])

    # Only the borrower of the booking can propose; the lender and outsiders cannot.
    assert (await propose(client, lena, booking_id)).status_code == 404
    assert (await propose(client, otto, booking_id)).status_code == 404
    past = await propose(client, ben, booking_id, meet_at=later(-1))
    assert past.status_code == 422
    naive = await propose(client, ben, booking_id, meet_at="2099-01-01T10:00:00")
    assert naive.status_code == 422
    assert (await propose(client, ben, booking_id, location="   ")).status_code == 422
    assert (await propose(client, ben, booking_id, price="-1")).status_code == 422

    first = (await propose(client, ben, booking_id)).json()
    duplicate = await propose(client, ben, booking_id)
    assert duplicate.status_code == 409

    # Outsiders cannot see or act on someone else's meetup.
    assert (await client.get(f"/meetups/{first['id']}", headers=otto.headers)).status_code == 404
    hijack = await client.post(f"/meetups/{first['id']}/accept", headers=otto.headers)
    assert hijack.status_code == 404

    # A proposed time that has passed can no longer be accepted, only countered or declined.
    sql("UPDATE meetups SET meet_at = now() - interval '1 hour' WHERE id = %s", first["id"])
    stale = (await client.get(f"/meetups/{first['id']}", headers=lena.headers)).json()
    assert stale["available_actions"] == ["counter", "decline"]
    assert (
        await client.post(f"/meetups/{first['id']}/accept", headers=lena.headers)
    ).status_code == 409

    declined = await client.post(
        f"/meetups/{first['id']}/decline", json={"message": "Sold it, sorry"}, headers=lena.headers
    )
    assert declined.json()["status"] == "declined"
    # Once closed, the borrower may start a fresh negotiation for the same booking.
    assert (await propose(client, ben, booking_id)).status_code == 201


async def test_meetups_need_a_confirmed_booking(client, make_user, sql):
    lena, ben = make_user("Lena"), make_user("Ben")
    listing = await create_listing(client, lena)

    # No standalone proposals: a listing alone is not enough.
    standalone = await client.post(
        "/meetups", json={"listing_id": listing["id"], **terms()}, headers=ben.headers
    )
    assert standalone.status_code == 422
    assert (await propose(client, ben, "00000000-0000-4000-8000-000000000000")).status_code == 404

    # Once the item is back, it is too late to propose any meetup.
    returned = await booked(client, ben, listing["id"], 5, 6)
    sql("UPDATE bookings SET state = 'returned' WHERE id = %s", returned)
    assert (await propose(client, ben, returned)).status_code == 409

    # Cancelling a booking cancels its meetup, and no new one can be proposed for it.
    booking_id = await booked(client, ben, listing["id"])
    meetup = (await propose(client, ben, booking_id)).json()
    cancelled = await client.post(f"/bookings/{booking_id}/cancel", headers=ben.headers)
    assert cancelled.status_code == 200, cancelled.text
    seen = (await client.get(f"/meetups/{meetup['id']}", headers=lena.headers)).json()
    assert seen["status"] == "cancelled"
    assert seen["events"][-1]["message"] == "Booking cancelled"
    assert (await propose(client, ben, booking_id)).status_code == 409


async def test_withdrawing_and_cancelling(client, make_user):
    lena, ben = make_user("Lena"), make_user("Ben")
    listing = await create_listing(client, lena)
    booking_id = await booked(client, ben, listing["id"])

    withdrawn = (await propose(client, ben, booking_id)).json()
    response = await client.post(f"/meetups/{withdrawn['id']}/cancel", headers=ben.headers)
    assert response.json()["status"] == "cancelled"

    meetup = (await propose(client, ben, booking_id)).json()
    # The lender can respond but not withdraw the borrower's offer.
    assert (
        await client.post(f"/meetups/{meetup['id']}/cancel", headers=lena.headers)
    ).status_code == 409
    await client.post(f"/meetups/{meetup['id']}/accept", headers=lena.headers)
    called_off = await client.post(
        f"/meetups/{meetup['id']}/cancel",
        json={"message": "Something came up"},
        headers=lena.headers,
    )
    assert called_off.status_code == 200
    assert called_off.json()["status"] == "cancelled"
    assert called_off.json()["available_actions"] == []


async def test_deleting_an_account_cancels_its_meetups(client, make_user):
    lena = make_user("Lena")
    listing = await create_listing(client, lena)
    signup = await client.post(
        "/auth/signup",
        json={
            "email": "ben@example.com",
            "password": "correct horse battery",
            "display_name": "Ben",
        },
    )
    client.cookies.clear()
    ben_headers = {"authorization": f"Bearer {issue_access_token(UUID(signup.json()['user_id']))}"}
    ben = type("Actor", (), {"headers": ben_headers})()
    booking_id = await booked(client, ben, listing["id"])
    meetup = (await propose(client, ben, booking_id)).json()
    # Account deletion is refused while the booking is live, so cancel it first. That already
    # closes the meetup; deletion then closes anything still open.
    await client.post(f"/bookings/{booking_id}/cancel", headers=ben_headers)

    deleted = await client.post(
        "/auth/me/delete", json={"password": "correct horse battery"}, headers=ben_headers
    )
    assert deleted.status_code == 204, deleted.text

    seen = (await client.get(f"/meetups/{meetup['id']}", headers=lena.headers)).json()
    assert seen["status"] == "cancelled"
    assert seen["borrower_display_name"] == "Deleted user"
    assert seen["events"][-1]["message"] == "Booking cancelled"


async def test_handover_and_return_meetups_complete_with_the_booking(client, make_user):
    lena, ben = make_user("Lena"), make_user("Ben")
    listing = await create_listing(client, lena)
    booking_id = await booked(client, ben, listing["id"])

    handover = (await propose(client, ben, booking_id)).json()
    assert handover["purpose"] == "handover"
    await client.post(f"/meetups/{handover['id']}/accept", headers=lena.headers)
    # The return meetup can only be proposed once the item has been handed over.
    early = await propose(client, ben, booking_id)
    assert early.status_code == 409

    assert (await checklist(client, lena, booking_id, "handover")).status_code == 200
    done = (await client.get(f"/meetups/{handover['id']}", headers=ben.headers)).json()
    assert done["status"] == "completed" and done["available_actions"] == []
    assert done["events"][-1]["kind"] == "complete"
    assert done["events"][-1]["message"] == "Handover recorded"

    giving_back = (await propose(client, ben, booking_id, location="Bishan MRT exit B")).json()
    assert giving_back["purpose"] == "return" and giving_back["status"] == "pending"
    assert (await propose(client, ben, booking_id)).status_code == 409  # one live return meetup

    assert (await checklist(client, ben, booking_id, "return")).status_code == 200
    back = (await client.get(f"/meetups/{giving_back['id']}", headers=lena.headers)).json()
    assert back["status"] == "completed"
    assert back["events"][-1]["message"] == "Return recorded"
    closed = (await client.get("/meetups?status=completed", headers=ben.headers)).json()
    assert {m["purpose"] for m in closed} == {"handover", "return"}
