"""Profile privacy, account isolation, photo ordering and booking preservation."""

import pytest

from tests.helpers import book, checklist, create_listing, upload

pytestmark = pytest.mark.anyio


async def test_profile_update_and_public_privacy(client, make_user):
    owner, other = make_user("Owner"), make_user("Other")
    avatar = await upload(client, owner, "avatar")
    updated = await client.patch(
        "/auth/me",
        headers=owner.headers,
        json={
            "display_name": "  New name  ",
            "bio": "I lend camping gear.",
            "avatar_key": avatar,
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["display_name"] == "New name"
    assert avatar in updated.json()["avatar_url"]
    public = (await client.get(f"/users/{owner.id}")).json()
    assert public["bio"] == "I lend camping gear."
    assert "email" not in public and "password_hash" not in public
    assert (await client.get("/auth/me", headers=other.headers)).json()["display_name"] == "Other"
    assert (await client.patch("/auth/me", json={"display_name": "Intruder"})).status_code == 401
    assert (
        await client.patch(
            "/auth/me", headers=other.headers, json={"display_name": "Other", "avatar_key": avatar}
        )
    ).status_code == 400
    assert (
        await client.patch("/auth/me", headers=owner.headers, json={"display_name": "   "})
    ).status_code == 422
    assert (
        await client.patch(
            "/auth/me",
            headers=owner.headers,
            json={"display_name": "Owner", "email": "changed@example.test"},
        )
    ).status_code == 422
    removed = await client.patch(
        "/auth/me",
        headers=owner.headers,
        json={"display_name": "Owner", "bio": "", "avatar_key": None},
    )
    assert removed.json()["avatar_url"] is None and removed.json()["bio"] is None


async def test_saved_items_are_private_idempotent_and_removable_when_archived(client, make_user):
    owner, borrower, other = make_user("Owner"), make_user("Borrower"), make_user("Other")
    item = await create_listing(client, owner)
    path = f"/saved-listings/{item['id']}"
    assert (await client.put(path)).status_code == 401
    for _ in range(2):
        assert (await client.put(path, headers=borrower.headers)).status_code == 204
    assert len((await client.get("/saved-listings", headers=borrower.headers)).json()) == 1
    assert (await client.get("/saved-listings", headers=other.headers)).json() == []
    await client.patch(
        f"/listings/{item['id']}", headers=owner.headers, json={"status": "archived"}
    )
    assert (await client.get("/saved-listings", headers=borrower.headers)).json()[0][
        "status"
    ] == "archived"
    assert (await client.put(path, headers=other.headers)).status_code == 404
    for _ in range(2):
        assert (await client.delete(path, headers=borrower.headers)).status_code == 204
    assert (await client.get("/saved-listings", headers=borrower.headers)).json() == []


async def test_photo_editing_preserves_rental_evidence_and_archive_is_reversible(client, make_user):
    owner, borrower = make_user("Owner"), make_user("Borrower")
    keys = [await upload(client, owner, "listing") for _ in range(3)]
    item = await create_listing(client, owner, photo_keys=keys[:2])
    assert item["photo_keys"] == keys[:2]
    booking = (await book(client, borrower, item["id"])).json()
    assert (await checklist(client, owner, booking["id"], "handover")).status_code == 200
    evidence_before = (
        await client.get(f"/bookings/{booking['id']}/checklists", headers=borrower.headers)
    ).json()
    edited = await client.patch(
        f"/listings/{item['id']}",
        headers=owner.headers,
        json={
            "category": "Travel",
            "mrt_station": "Bugis",
            "photo_keys": [keys[1], keys[2]],
            "status": "archived",
        },
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["photo_keys"] == [keys[1], keys[2]]
    assert edited.json()["mrt_station"] == "Bugis"
    assert (
        await client.get(f"/bookings/{booking['id']}/checklists", headers=borrower.headers)
    ).json() == evidence_before
    assert (await client.get(f"/listings/{item['id']}")).status_code == 404
    assert (
        await client.get(f"/listings/{item['id']}/manage", headers=borrower.headers)
    ).status_code == 404
    assert (
        await client.get(f"/listings/{item['id']}/manage", headers=owner.headers)
    ).status_code == 200
    assert (
        await client.patch(
            f"/listings/{item['id']}", headers=owner.headers, json={"status": "active"}
        )
    ).status_code == 200
    assert (await client.get(f"/bookings/{booking['id']}", headers=borrower.headers)).json()[
        "state"
    ] == "handed_over"


async def test_media_cannot_be_stolen_or_reused_across_listings(client, make_user):
    owner, other = make_user("Owner"), make_user("Other")
    key = await upload(client, owner, "listing")
    first = await create_listing(client, owner, photo_keys=[key])
    second = await create_listing(client, owner)
    third = await create_listing(client, other)
    assert (
        await client.patch(
            f"/listings/{second['id']}", headers=owner.headers, json={"photo_keys": [key]}
        )
    ).status_code == 409
    assert (
        await client.patch(
            f"/listings/{third['id']}", headers=other.headers, json={"photo_keys": [key]}
        )
    ).status_code == 400
    assert (
        await client.patch(
            f"/listings/{first['id']}", headers=owner.headers, json={"photo_keys": [key, key]}
        )
    ).status_code == 400
    assert (await client.get(f"/listings/{first['id']}")).json()["photo_keys"] == [key]


async def test_sorting_and_owner_filter_only_include_active_listings(client, make_user):
    owner, other = make_user("Owner"), make_user("Other")
    cheap = await create_listing(client, owner, price_day="2")
    expensive = await create_listing(client, owner, price_day="30")
    await create_listing(client, other, price_day="1")
    for sort, expected in [
        ("price_asc", [cheap["id"], expensive["id"]]),
        ("price_desc", [expensive["id"], cheap["id"]]),
    ]:
        results = await client.get("/listings", params={"owner_id": str(owner.id), "sort": sort})
        assert [item["id"] for item in results.json()] == expected
    await client.patch(f"/listings/{cheap['id']}", headers=owner.headers, json={"status": "paused"})
    results = await client.get("/listings", params={"owner_id": str(owner.id)})
    assert [item["id"] for item in results.json()] == [expensive["id"]]


async def test_photo_append_respects_order_and_limit(client, make_user):
    owner = make_user("Owner")
    keys = [await upload(client, owner, "listing") for _ in range(11)]
    item = await create_listing(client, owner, photo_keys=keys[:10])
    assert item["photo_keys"] == keys[:10]
    extra = await client.post(
        "/media", headers=owner.headers, json={"listing_id": item["id"], "key": keys[10]}
    )
    assert extra.status_code == 400
    await client.patch(
        f"/listings/{item['id']}", headers=owner.headers, json={"photo_keys": keys[1:10]}
    )
    extra = await client.post(
        "/media", headers=owner.headers, json={"listing_id": item["id"], "key": keys[10]}
    )
    assert extra.status_code == 201, extra.text
    assert (await client.get(f"/listings/{item['id']}")).json()["photo_keys"] == keys[1:11]
