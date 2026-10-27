"""Mock gateway behavior and reconciliation with booking lifecycle events."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.transactions.release import handle_release
from tests.helpers import book, checklist, create_listing

pytestmark = pytest.mark.anyio


async def test_successful_booking_captures_total_and_exposes_audit_trail(
    client, make_user, sql
):
    lender, borrower, stranger = make_user("Lena"), make_user("Ben"), make_user("Sam")
    listing = await create_listing(client, lender)

    response = await book(client, borrower, listing["id"])

    assert response.status_code == 201, response.text
    booking = response.json()
    payment_response = await client.get(
        f"/payments/bookings/{booking['id']}", headers=borrower.headers
    )
    assert payment_response.status_code == 200
    payment = payment_response.json()
    assert payment["amount"] == "116.00"
    assert payment["currency"] == "SGD"
    assert payment["status"] == "captured"
    assert payment["provider"] == "mock"
    assert payment["payment_method_label"] == "Mock Visa ending 4242"
    assert [(op["operation"], op["amount"]) for op in payment["operations"]] == [
        ("charge", "116.00")
    ]
    assert (
        await client.get(f"/payments/bookings/{booking['id']}", headers=lender.headers)
    ).status_code == 200
    assert (
        await client.get(f"/payments/bookings/{booking['id']}", headers=stranger.headers)
    ).status_code == 404
    assert sql("SELECT count(*) FROM payments")[0][0] == 1


@pytest.mark.parametrize(
    ("token", "code", "retryable"),
    [
        ("pm_mock_declined", "card_declined", False),
        ("pm_mock_insufficient_funds", "insufficient_funds", False),
        ("pm_mock_expired", "expired_payment_method", False),
        ("pm_mock_processing_error", "processing_error", True),
    ],
)
async def test_failed_payment_rolls_back_booking_and_ledger(
    client, make_user, sql, token, code, retryable
):
    lender, borrower = make_user("Lena"), make_user("Ben")
    listing = await create_listing(client, lender)

    response = await book(
        client, borrower, listing["id"], payment_method_token=token
    )

    assert response.status_code == 402
    assert response.json()["detail"]["code"] == code
    assert response.json()["detail"]["retryable"] is retryable
    assert sql("SELECT count(*) FROM bookings")[0][0] == 0
    assert sql("SELECT count(*) FROM payments")[0][0] == 0
    assert sql("SELECT count(*) FROM ledger_entries")[0][0] == 0


async def test_cancellation_refunds_the_full_charge_once(client, make_user):
    lender, borrower = make_user("Lena"), make_user("Ben")
    listing = await create_listing(client, lender)
    booking = (await book(client, borrower, listing["id"])).json()

    cancelled = await client.post(
        f"/bookings/{booking['id']}/cancel", headers=borrower.headers
    )

    assert cancelled.status_code == 200
    payment = (
        await client.get(f"/payments/bookings/{booking['id']}", headers=borrower.headers)
    ).json()
    assert payment["status"] == "refunded"
    assert [(op["operation"], op["amount"]) for op in payment["operations"]] == [
        ("charge", "116.00"),
        ("refund", "116.00"),
    ]
    repeated = await client.post(
        f"/bookings/{booking['id']}/cancel", headers=borrower.headers
    )
    assert repeated.status_code == 409


async def test_return_refund_and_fee_payout_reconcile_to_capture(client, make_user):
    lender, borrower = make_user("Lena"), make_user("Ben")
    listing = await create_listing(client, lender)
    booking = (await book(client, borrower, listing["id"])).json()
    await checklist(client, lender, booking["id"], "handover")
    await checklist(client, borrower, booking["id"], "return")

    settled = await client.post(f"/bookings/{booking['id']}/settle", headers=lender.headers)
    assert settled.status_code == 200
    later = datetime.now(UTC) + timedelta(days=8)
    assert (await handle_release(booking["id"], later))["status"] == "released"

    payment = (
        await client.get(f"/payments/bookings/{booking['id']}", headers=borrower.headers)
    ).json()
    operations = [(op["operation"], Decimal(op["amount"])) for op in payment["operations"]]
    assert operations == [
        ("charge", Decimal("116.00")),
        ("refund", Decimal("80.00")),
        ("payout", Decimal("36.00")),
    ]
    assert sum(amount for kind, amount in operations if kind != "charge") == Decimal("116.00")


async def test_damage_refunds_remainder_and_pays_lender_share(client, make_user):
    lender, borrower = make_user("Lena"), make_user("Ben")
    listing = await create_listing(client, lender)
    booking = (await book(client, borrower, listing["id"])).json()
    await checklist(client, borrower, booking["id"], "handover")
    await checklist(client, lender, booking["id"], "return")

    response = await client.post(
        f"/bookings/{booking['id']}/damage",
        json={"severity": "moderate", "notes": "Torn flysheet"},
        headers=lender.headers,
    )

    assert response.status_code == 200
    payment = (
        await client.get(f"/payments/bookings/{booking['id']}", headers=lender.headers)
    ).json()
    assert [(op["operation"], op["amount"]) for op in payment["operations"]] == [
        ("charge", "116.00"),
        ("refund", "48.00"),
        ("payout", "32.00"),
    ]
