"""Account deletion: personal data is erased, other people's records stay intact."""

from uuid import UUID

import pytest

from app.auth.dependencies import issue_access_token
from tests.helpers import book, create_listing, upload

pytestmark = pytest.mark.anyio

EMAIL, PASSWORD = "lena@example.com", "correct horse battery"


async def signup_lena(client) -> tuple[UUID, dict[str, str]]:
    response = await client.post(
        "/auth/signup", json={"email": EMAIL, "password": PASSWORD, "display_name": "Lena"}
    )
    assert response.status_code == 201, response.text
    user_id = UUID(response.json()["user_id"])
    client.cookies.clear()  # act through explicit tokens, so each request names its user
    return user_id, {"authorization": f"Bearer {issue_access_token(user_id)}"}


class Lena:
    def __init__(self, user_id: UUID, headers: dict[str, str]) -> None:
        self.id, self.headers, self.name = user_id, headers, "Lena"


async def test_delete_account_erases_person_and_keeps_history(client, make_user, sql):
    lena = Lena(*await signup_lena(client))
    ben, other = make_user("Ben"), make_user("Otto")
    await client.patch(
        "/auth/me", json={"display_name": "Lena", "bio": "I lend tools"}, headers=lena.headers
    )

    photo = await upload(client, lena, "listing")
    rented = await create_listing(
        client,
        lena,
        title="Rented drill",
        photo_keys=[photo],
        description="Pick up at my block 123",
    )
    never = await create_listing(client, lena, title="Never rented ladder")
    booking = (await book(client, ben, rented["id"])).json()
    assert (
        await client.post(f"/bookings/{booking['id']}/cancel", headers=ben.headers)
    ).status_code == 200
    others = await create_listing(client, other, title="Otto's tent")
    await client.put(f"/saved-listings/{others['id']}", headers=lena.headers)
    sql(
        "INSERT INTO reviews (booking_id, author_id, target_id, rating, comment) "
        "VALUES (%s, %s, %s, 5, 'Great borrower')",
        booking["id"],
        lena.id,
        ben.id,
    )

    preview = await client.get("/auth/me/deletion", headers=lena.headers)
    assert preview.json() == {
        "allowed": True,
        "open_rentals": 0,
        "listings_deleted": 1,
        "listings_archived": 1,
    }

    wrong = await client.post("/auth/me/delete", json={"password": "nope"}, headers=lena.headers)
    assert wrong.status_code == 403
    deleted = await client.post(
        "/auth/me/delete", json={"password": PASSWORD}, headers=lena.headers
    )
    assert deleted.status_code == 204, deleted.text

    # The old session and the old credentials no longer work; the email is free again.
    assert (await client.get("/auth/me", headers=lena.headers)).status_code == 401
    login = await client.post("/auth/session", json={"email": EMAIL, "password": PASSWORD})
    assert login.status_code == 401

    # Personal data is gone from the user row.
    [(email, pw, name, bio, avatar, deleted_at)] = sql(
        "SELECT email, password_hash, display_name, bio, avatar_key, deleted_at FROM users "
        "WHERE id = %s",
        lena.id,
    )
    assert email == f"deleted-{lena.id}@deleted.invalid" and pw == "!deleted"
    assert (name, bio, avatar) == ("Deleted user", None, None) and deleted_at is not None
    profile = (await client.get(f"/users/{lena.id}")).json()
    assert profile["display_name"] == "Deleted user" and profile["bio"] is None

    # Listings: the unrented one is gone; the rented one is archived and scrubbed.
    assert sql("SELECT count(*) FROM listings WHERE id = %s", never["id"]) == [(0,)]
    [(status, description, lat, lng)] = sql(
        "SELECT status, description, latitude, longitude FROM listings WHERE id = %s", rented["id"]
    )
    assert (status, description, lat, lng) == ("archived", None, None, None)
    assert sql(
        "SELECT count(*) FROM media WHERE stage = 'listing' AND uploaded_by = %s", lena.id
    ) == [(0,)]
    assert sql("SELECT count(*) FROM availability WHERE listing_id = %s", rented["id"]) == [(0,)]
    assert sql("SELECT count(*) FROM saved_listings WHERE user_id = %s", lena.id) == [(0,)]

    # Other people's history is intact.
    theirs = await client.get(f"/bookings/{booking['id']}", headers=ben.headers)
    assert theirs.status_code == 200 and theirs.json()["listing_title"] == "Rented drill"
    ledger = await client.get(f"/bookings/{booking['id']}/ledger", headers=ben.headers)
    assert ledger.status_code == 200 and len(ledger.json()) == 8
    [review] = (await client.get("/reviews", params={"user_id": str(ben.id)})).json()
    assert review["author_display_name"] == "Deleted user" and review["rating"] == 5

    again = await client.post(
        "/auth/signup", json={"email": EMAIL, "password": PASSWORD, "display_name": "Lena"}
    )
    assert again.status_code == 201


async def test_delete_account_blocked_while_renting(client, make_user):
    lena = Lena(*await signup_lena(client))
    owner = make_user("Otto")
    listing = await create_listing(client, owner)
    assert (await book(client, lena, listing["id"])).status_code == 201

    preview = (await client.get("/auth/me/deletion", headers=lena.headers)).json()
    assert preview["allowed"] is False and preview["open_rentals"] == 1
    blocked = await client.post(
        "/auth/me/delete", json={"password": PASSWORD}, headers=lena.headers
    )
    assert blocked.status_code == 409
    assert (await client.get("/auth/me", headers=lena.headers)).status_code == 200


async def test_lender_with_active_booking_cannot_delete(client, make_user):
    lena = Lena(*await signup_lena(client))
    listing = await create_listing(client, lena)
    assert (await book(client, make_user("Ben"), listing["id"])).status_code == 201
    blocked = await client.post(
        "/auth/me/delete", json={"password": PASSWORD}, headers=lena.headers
    )
    assert blocked.status_code == 409
