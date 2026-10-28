"""B3: listings, search filters, listing limits, location and price suggestions."""

from decimal import Decimal

import pytest

from app.catalogue import price_suggestion
from app.catalogue.mrt_stations import nearest_station
from app.catalogue.router import _locate
from app.integrations import onemap
from tests.helpers import book, create_listing, days

pytestmark = pytest.mark.anyio


async def test_search_filters(client, make_user):
    lender_a, lender_b, borrower = make_user("Ann"), make_user("Bo"), make_user("Cy")
    tent = await create_listing(client, lender_a)
    drill = await create_listing(
        client,
        lender_b,
        title="Cordless drill set",
        category="Tools",
        mrt_station="Bishan",
        price_day="9.00",
    )
    camera = await create_listing(
        client,
        lender_b,
        title="Fujifilm camera kit",
        category="Electronics",
        mrt_station="Bishan",
        price_day="28.00",
    )

    async def ids(**params) -> set[str]:
        response = await client.get("/listings", params=params)
        assert response.status_code == 200, response.text
        return {listing["id"] for listing in response.json()}

    assert await ids() == {tent["id"], drill["id"], camera["id"]}
    assert await ids(q="drill") == {drill["id"]}
    assert await ids(q="fuji") == {camera["id"]}  # partial word via ILIKE
    assert await ids(mrt="bishan") == {drill["id"], camera["id"]}
    assert await ids(planning_area="Clementi") == {tent["id"]}
    assert await ids(category="Tools") == {drill["id"]}
    assert await ids(max_price="10") == {drill["id"]}

    assert (await book(client, borrower, tent["id"], 0, 2)).status_code == 201
    free = await ids(**{"from": days(1), "to": days(4)})
    assert tent["id"] not in free and drill["id"] in free

    paused = await client.patch(
        f"/listings/{drill['id']}", json={"status": "paused"}, headers=lender_b.headers
    )
    assert paused.json()["status"] == "paused"
    assert drill["id"] not in await ids()
    mine = await client.get("/listings/mine", headers=lender_b.headers)
    assert {listing["id"] for listing in mine.json()} == {drill["id"], camera["id"]}


async def test_free_listing_limit_is_three(client, make_user):
    lender = make_user("Lena")
    listings = [await create_listing(client, lender, title=f"Item {i}") for i in range(3)]
    fourth = await client.post(
        "/listings",
        json={
            "title": "Item 4",
            "category": "Tools",
            "condition": "Good",
            "price_day": "5.00",
            "deposit": "0",
            "mrt_station": "Bedok",
        },
        headers=lender.headers,
    )
    assert fourth.status_code == 403
    archived = await client.patch(
        f"/listings/{listings[0]['id']}", json={"status": "archived"}, headers=lender.headers
    )
    assert archived.status_code == 200
    await create_listing(client, lender, title="Item 4")


async def test_archive_blocked_by_confirmed_booking(client, make_user):
    lender, borrower = make_user("Lena"), make_user("Ben")
    listing = await create_listing(client, lender)
    booking = (await book(client, borrower, listing["id"])).json()
    blocked = await client.patch(
        f"/listings/{listing['id']}", json={"status": "archived"}, headers=lender.headers
    )
    assert blocked.status_code == 409
    cancelled = await client.post(f"/bookings/{booking['id']}/cancel", headers=lender.headers)
    assert cancelled.status_code == 200, cancelled.text
    archived = await client.patch(
        f"/listings/{listing['id']}", json={"status": "archived"}, headers=lender.headers
    )
    assert archived.status_code == 200
    assert (await client.get(f"/listings/{listing['id']}")).status_code == 404


async def test_listing_validation_and_ownership(client, make_user):
    lender, other = make_user("Lena"), make_user("Otto")
    no_location = await client.post(
        "/listings",
        json={
            "title": "Tent",
            "category": "Outdoor",
            "condition": "Good",
            "price_day": "5",
            "deposit": "0",
        },
        headers=lender.headers,
    )
    assert no_location.status_code == 422
    listing = await create_listing(client, lender)
    hijack = await client.patch(
        f"/listings/{listing['id']}", json={"price_day": "1.00"}, headers=other.headers
    )
    assert hijack.status_code == 404
    windows = await client.put(
        f"/listings/{listing['id']}/availability",
        json={"windows": [{"start_date": days(0), "end_date": days(3)}]},
        headers=lender.headers,
    )
    assert windows.status_code == 200
    assert (await book(client, other, listing["id"], 2, 5)).status_code == 409


async def test_locate_uses_onemap_then_nearest_station(monkeypatch):
    async def fake_geocode(postal_code: str):
        return onemap.GeocodeResult(1.3152, 103.7650, None)  # beside Clementi MRT

    monkeypatch.setattr("app.catalogue.router.geocode_postal_code", fake_geocode)
    from app.catalogue.router import ListingCreate

    request = ListingCreate(
        title="Tent",
        category="Outdoor",
        condition="Good",
        price_day=Decimal("5"),
        deposit=Decimal("0"),
        postal_code="120345",
    )
    assert (await _locate(request))[2:] == ("Clementi", "Clementi")
    assert nearest_station(1.3500, 103.8485).name == "Bishan"


class FakeLlm:
    name = "fake"

    def __init__(self, reply: str) -> None:
        self.reply = reply

    async def complete(self, prompt: str) -> str:
        return self.reply


VALID = """```json
{"day": {"min": 8, "recommended": 10, "max": 12},
 "week": {"min": 40, "recommended": 50, "max": 60},
 "month": {"min": 120, "recommended": 150, "max": 180}}
```"""


@pytest.mark.parametrize(
    ("reply", "source"),
    [
        (VALID, "llm"),
        ("Sure! Around $10 a day.", "heuristic"),
        (VALID.replace('"recommended": 50', '"recommended": 90'), "heuristic"),  # >= 7x day
    ],
)
async def test_price_suggestion_validates_model_output(
    client, make_user, monkeypatch, reply, source
):
    price_suggestion._cache.clear()
    monkeypatch.setattr(price_suggestion, "get_llm_client", lambda: FakeLlm(reply))
    user = make_user("Lena")
    response = await client.post(
        "/listings/price-suggestion",
        json={"title": "Camping tent", "category": "Outdoor", "condition": "Good"},
        headers=user.headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["source"] == source
    for period in ("day", "week", "month"):
        band = {k: Decimal(v) for k, v in body[period].items()}
        assert 0 < band["min"] <= band["recommended"] <= band["max"]


def test_heuristic_uses_median_of_comparables():
    prices = price_suggestion.heuristic_prices(
        [Decimal("10"), Decimal("20"), Decimal("12")], "Good"
    )
    assert prices["day"]["recommended"] == Decimal("12.00")
    assert prices["week"]["recommended"] < 7 * prices["day"]["recommended"]
    assert prices["month"]["recommended"] < 4 * prices["week"]["recommended"]
