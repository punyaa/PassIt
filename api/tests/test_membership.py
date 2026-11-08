"""PassIt Plus memberships: plan capture at signup, deposit perks, plan changes, expiry."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.memberships.renewal import expire_due_memberships
from app.transactions.release import release_due_fees
from tests.helpers import book, checklist, create_listing

pytestmark = pytest.mark.anyio


async def signup(client, name, plan=None):
    payload = {
        "email": f"{name.lower()}@example.com",
        "password": "password-123",
        "display_name": name,
    }
    if plan is not None:
        payload["plan"] = plan
    response = await client.post("/auth/signup", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def ledger_sum(sql, booking_id, account=None):
    query = "SELECT COALESCE(SUM(amount), 0) FROM ledger_entries WHERE booking_id = %s"
    params: tuple = (booking_id,)
    if account:
        query += " AND account = %s"
        params += (account,)
    return sql(query, *params)[0][0]


async def test_signup_with_plan_sets_membership(client):
    await signup(client, "EcoUser", plan="eco-saver")
    me = await client.get("/auth/me")
    assert me.json()["plan"] == "eco-saver"

    membership = await client.get("/memberships/me")
    assert membership.status_code == 200, membership.text
    body = membership.json()
    assert body["plan"] == "eco-saver"
    assert body["status"] == "active"
    assert body["current_period_end"] is not None
    assert body["perks"]["deposit_factor"] == "0.75"


async def test_signup_defaults_to_saver(client, sql):
    user = await signup(client, "SaverUser")
    me = await client.get("/auth/me")
    assert me.json()["plan"] == "saver"

    rows = sql(
        "SELECT plan, status, current_period_end FROM memberships WHERE user_id = %s",
        user["user_id"],
    )
    assert len(rows) == 1
    assert rows[0][0] == "saver" and rows[0][1] == "active" and rows[0][2] is None


async def test_booking_deposit_follows_plan(client, make_user):
    lender = make_user("Lena")
    saver, eco, mega = make_user("Sue"), make_user("Eli"), make_user("Max")
    listing = await create_listing(client, lender, deposit="80.00")

    unknown = await client.get("/memberships/me", headers=saver.headers)
    assert unknown.status_code == 404  # fixture users have no membership row yet

    for user, plan in ((eco, "eco-saver"), (mega, "mega-saver")):
        chosen = await client.post(
            "/memberships/me", json={"plan": plan}, headers=user.headers
        )
        assert chosen.status_code == 200, chosen.text
        assert chosen.json()["plan"] == plan

    saver_booking = (await book(client, saver, listing["id"], 0, 2)).json()
    eco_booking = (await book(client, eco, listing["id"], 3, 5)).json()
    mega_booking = (await book(client, mega, listing["id"], 6, 8)).json()
    assert saver_booking["deposit"] == "80.00"
    assert eco_booking["deposit"] == "60.00"  # 25% lower deposits
    assert mega_booking["deposit"] == "0.00"  # zero deposits


async def test_mega_saver_zero_deposit_full_journey(client, make_user, sql):
    lender, borrower = make_user("Lena"), make_user("Max")
    listing = await create_listing(client, lender, deposit="80.00")
    chosen = await client.post(
        "/memberships/me", json={"plan": "mega-saver"}, headers=borrower.headers
    )
    assert chosen.status_code == 200, chosen.text

    booking = (await book(client, borrower, listing["id"])).json()
    assert booking["deposit"] == "0.00"
    assert ledger_sum(sql, booking["id"]) == 0

    assert (await checklist(client, lender, booking["id"], "handover")).status_code == 200
    assert (await checklist(client, borrower, booking["id"], "return")).status_code == 200
    settled = await client.post(f"/bookings/{booking['id']}/settle", headers=lender.headers)
    assert settled.json()["state"] == "settled"

    later = datetime.now(UTC) + timedelta(days=8)
    assert [r["status"] for r in await release_due_fees(later)] == ["released"]
    assert ledger_sum(sql, booking["id"]) == 0
    assert ledger_sum(sql, booking["id"], "platform_hold") == 0
    assert ledger_sum(sql, booking["id"], "lender") == Decimal("36.00")
    assert ledger_sum(sql, booking["id"], "borrower") == Decimal("-36.00")


async def test_membership_expiry_downgrades_to_saver(client, sql):
    await signup(client, "ExpiringUser", plan="eco-saver")
    sql(
        "UPDATE memberships SET current_period_end = now() - interval '1 day' "
        "WHERE plan = 'eco-saver'"
    )

    assert [r["status"] for r in await expire_due_memberships()] == ["expired"]
    assert [r["status"] for r in await expire_due_memberships()] == []  # idempotent

    me = await client.get("/auth/me")
    assert me.json()["plan"] == "saver"  # expired members fall back to free Saver
    events = sql(
        "SELECT event FROM membership_events e JOIN memberships m ON m.id = e.membership_id "
        "ORDER BY e.created_at, e.id"
    )
    assert [row[0] for row in events] == ["created", "expired"]


async def test_change_plan_records_events(client):
    await signup(client, "ChangerUser", plan="eco-saver")
    upgraded = await client.post("/memberships/me", json={"plan": "mega-saver"})
    assert upgraded.json()["plan"] == "mega-saver"
    downgraded = await client.post("/memberships/me", json={"plan": "saver"})
    assert downgraded.json()["plan"] == "saver"
    assert downgraded.json()["status"] == "active"
    assert downgraded.json()["current_period_end"] is None  # Saver never expires

    membership = (await client.get("/memberships/me")).json()
    assert membership["plan"] == "saver"


async def test_invalid_plan_rejected(client, make_user):
    bad_signup = await client.post(
        "/auth/signup",
        json={"email": "bad@example.com", "password": "password-123",
              "display_name": "Bad", "plan": "platinum"},
    )
    assert bad_signup.status_code == 422
    user = make_user("Uma")
    bad_change = await client.post(
        "/memberships/me", json={"plan": "platinum"}, headers=user.headers
    )
    assert bad_change.status_code == 422


async def choose(client, user, plan):
    chosen = await client.post("/memberships/me", json={"plan": plan}, headers=user.headers)
    assert chosen.status_code == 200, chosen.text
    return chosen.json()


async def test_listing_limit_follows_lender_plan(client, make_user):
    saver, prime, mega = make_user("Sam"), make_user("Pia"), make_user("Mo")
    await choose(client, prime, "eco-saver")
    await choose(client, mega, "mega-saver")

    for i in range(3):
        await create_listing(client, saver, title=f"Saver item {i}")
    blocked = await client.post(
        "/listings",
        json={
            "title": "One too many",
            "category": "Tools",
            "condition": "Good",
            "price_day": "5.00",
            "deposit": "0",
            "mrt_station": "Bedok",
        },
        headers=saver.headers,
    )
    assert blocked.status_code == 403
    assert "upgrade to PassIt Plus" in blocked.json()["detail"]

    for i in range(10):
        await create_listing(client, prime, title=f"Prime item {i}")  # Prime: up to 10
    eleventh = await client.post(
        "/listings",
        json={
            "title": "Prime item 10",
            "category": "Tools",
            "condition": "Good",
            "price_day": "5.00",
            "deposit": "0",
            "mrt_station": "Bedok",
        },
        headers=prime.headers,
    )
    assert eleventh.status_code == 403

    for i in range(11):
        await create_listing(client, mega, title=f"Mega item {i}")  # Mega: unlimited


async def test_payout_hold_follows_lender_plan(client, make_user):
    borrower = make_user("Bea")
    holds = {}
    for name, plan in (("Lia", None), ("Lou", "eco-saver"), ("Lex", "mega-saver")):
        lender = make_user(name)
        if plan:
            await choose(client, lender, plan)
        listing = await create_listing(client, lender)
        booking = (await book(client, borrower, listing["id"])).json()
        handed = await checklist(client, lender, booking["id"], "handover")
        assert handed.status_code == 200, handed.text
        body = handed.json()
        released = datetime.fromisoformat(body["fee_release_at"])
        handed_at = datetime.fromisoformat(body["handed_over_at"])
        holds[plan or "saver"] = released - handed_at

    assert holds["saver"] == timedelta(days=7)
    assert holds["eco-saver"] == timedelta(days=3)  # Prime: payouts in 3 days
    assert holds["mega-saver"] == timedelta(hours=1)  # Mega: same-day payouts


async def test_membership_exposes_lender_perks(client, make_user):
    user = make_user("Perky")
    prime = (await choose(client, user, "eco-saver"))["perks"]
    assert prime["listing_limit"] == 10
    assert prime["payout_hold_minutes"] == 3 * 24 * 60
    mega = (await choose(client, user, "mega-saver"))["perks"]
    assert mega["listing_limit"] is None
    assert mega["payout_hold_minutes"] == 60
