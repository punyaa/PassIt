"""Meetups: borrower and lender take turns until one accepts the other's terms."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from app.auth.dependencies import issue_access_token
from tests.helpers import create_listing

pytestmark = pytest.mark.anyio


def later(hours: int) -> str:
    return (datetime.now(UTC) + timedelta(hours=hours)).isoformat()


def terms(hours: int = 48, location: str = "Clementi MRT exit A", price: str = "30.00", **extra):
    return {"meet_at": later(hours), "location": location, "price": price, **extra}


async def propose(client, borrower, listing_id: str, **overrides):
    return await client.post(
        "/meetups",
        json={"listing_id": listing_id, **terms(), **overrides},
        headers=borrower.headers,
    )


async def test_borrower_and_lender_negotiate_then_meeting_is_scheduled(client, make_user):
    lena, ben = make_user("Lena"), make_user("Ben")
    listing = await create_listing(client, lena)

    created = await propose(client, ben, listing["id"], message="Could we meet after work?")
    assert created.status_code == 201, created.text
    meetup = created.json()
    assert meetup["status"] == "pending"
    assert meetup["awaiting_role"] == "lender"
    assert meetup["viewer_role"] == "borrower"
    assert meetup["available_actions"] == ["cancel"]
    assert meetup["listing_title"] == listing["title"]
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

    assert (await propose(client, lena, listing["id"])).status_code == 400
    past = await propose(client, ben, listing["id"], meet_at=later(-1))
    assert past.status_code == 422
    naive = await propose(client, ben, listing["id"], meet_at="2099-01-01T10:00:00")
    assert naive.status_code == 422
    assert (await propose(client, ben, listing["id"], location="   ")).status_code == 422
    assert (await propose(client, ben, listing["id"], price="-1")).status_code == 422

    first = (await propose(client, ben, listing["id"])).json()
    duplicate = await propose(client, ben, listing["id"])
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
    # Once closed, the borrower may start a fresh negotiation.
    assert (await propose(client, ben, listing["id"])).status_code == 201

    # Paused listings take no new proposals.
    await client.patch(
        f"/listings/{listing['id']}", json={"status": "paused"}, headers=lena.headers
    )
    assert (await propose(client, otto, listing["id"])).status_code == 404


async def test_withdrawing_and_cancelling(client, make_user):
    lena, ben = make_user("Lena"), make_user("Ben")
    listing = await create_listing(client, lena)

    withdrawn = (await propose(client, ben, listing["id"])).json()
    response = await client.post(f"/meetups/{withdrawn['id']}/cancel", headers=ben.headers)
    assert response.json()["status"] == "cancelled"

    meetup = (await propose(client, ben, listing["id"])).json()
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
    meetup = (
        await client.post(
            "/meetups", json={"listing_id": listing["id"], **terms()}, headers=ben_headers
        )
    ).json()

    deleted = await client.post(
        "/auth/me/delete", json={"password": "correct horse battery"}, headers=ben_headers
    )
    assert deleted.status_code == 204, deleted.text

    seen = (await client.get(f"/meetups/{meetup['id']}", headers=lena.headers)).json()
    assert seen["status"] == "cancelled"
    assert seen["borrower_display_name"] == "Deleted user"
    assert seen["events"][-1]["message"] == "Account deleted"
