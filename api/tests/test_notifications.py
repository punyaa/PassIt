"""Booking and release events: what the API publishes, and how."""

import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.core.config import Settings
from app.integrations import notifications
from app.transactions.release import handle_release, release_due_fees
from tests.helpers import book, checklist, create_listing

pytestmark = pytest.mark.anyio


class Recorder:
    def __init__(self) -> None:
        self.events: list[dict] = []

    def publish(self, event: dict) -> None:
        self.events.append(event)

    @property
    def types(self) -> list[str]:
        return [event["type"] for event in self.events]


@pytest.fixture
def published(monkeypatch: pytest.MonkeyPatch) -> Recorder:
    recorder = Recorder()
    monkeypatch.setattr(notifications, "get_publisher", lambda: recorder)
    return recorder


async def test_each_booking_step_publishes_one_event(client, make_user, published):
    lender, borrower = make_user("Lena"), make_user("Ben")
    listing = await create_listing(client, lender)

    booking = (await book(client, borrower, listing["id"], 0, 2)).json()
    await checklist(client, lender, booking["id"], "handover")
    await checklist(client, borrower, booking["id"], "return")
    await client.post(f"/bookings/{booking['id']}/settle", headers=lender.headers)

    assert published.types == [
        "booking.confirmed",
        "booking.handed_over",
        "booking.returned",
        "booking.settled",
    ]
    confirmed = published.events[0]
    assert confirmed["version"] == 1 and confirmed["actor"] == "borrower"
    assert confirmed["booking"]["id"] == booking["id"]
    assert confirmed["booking"]["listing_title"] == listing["title"]
    assert confirmed["booking"]["fee"] == "36.00" and confirmed["booking"]["deposit"] == "80.00"
    assert confirmed["borrower"] == {"name": "Ben", "email": borrower_email(confirmed)}
    assert confirmed["lender"]["name"] == "Lena"
    assert len({event["event_id"] for event in published.events}) == 4
    json.dumps(published.events)  # every event must be JSON-ready for SNS


def borrower_email(event: dict) -> str:
    return event["borrower"]["email"]


async def test_cancelling_and_damage_are_published_with_their_details(client, make_user, published):
    lender, borrower = make_user("Lena"), make_user("Ben")
    listing = await create_listing(client, lender)

    cancelled = (await book(client, borrower, listing["id"], 0, 1)).json()
    await client.post(f"/bookings/{cancelled['id']}/cancel", headers=borrower.headers)

    damaged = (await book(client, borrower, listing["id"], 5, 6)).json()
    await checklist(client, lender, damaged["id"], "handover")
    await checklist(client, borrower, damaged["id"], "return")
    await client.post(
        f"/bookings/{damaged['id']}/damage",
        json={"severity": "moderate", "notes": "scratch"},
        headers=lender.headers,
    )

    cancel_event = next(e for e in published.events if e["type"] == "booking.cancelled")
    assert cancel_event["actor"] == "borrower"
    settle_event = published.events[-1]
    assert settle_event["type"] == "booking.settled"
    assert settle_event["booking"]["damage_severity"] == "moderate"


async def test_a_failed_booking_publishes_nothing(client, make_user, published):
    lender, borrower, other = make_user("Lena"), make_user("Ben"), make_user("Cy")
    listing = await create_listing(client, lender)
    assert (await book(client, borrower, listing["id"], 0, 2)).status_code == 201
    assert (await book(client, other, listing["id"], 1, 3)).status_code == 409
    assert published.types == ["booking.confirmed"]


async def test_a_broken_publisher_never_fails_the_booking(client, make_user, monkeypatch):
    class Broken:
        def publish(self, event: dict) -> None:
            raise RuntimeError("SNS is down")

    monkeypatch.setattr(notifications, "get_publisher", lambda: Broken())
    lender, borrower = make_user("Lena"), make_user("Ben")
    listing = await create_listing(client, lender)
    assert (await book(client, borrower, listing["id"], 0, 2)).status_code == 201


async def test_fee_release_returns_its_event_once(client, make_user, published):
    lender, borrower = make_user("Lena"), make_user("Ben")
    listing = await create_listing(client, lender)
    booking = (await book(client, borrower, listing["id"], 0, 2)).json()
    await checklist(client, lender, booking["id"], "handover")
    later = datetime.now(UTC) + timedelta(days=8)

    result = await handle_release(booking["id"], later)
    assert result["status"] == "released"
    assert result["event"]["type"] == "fee.released"
    assert result["event"]["lender"]["name"] == "Lena"
    json.dumps(result)  # the Lambda returns this, and a destination forwards it

    again = await handle_release(booking["id"], later)
    assert again["status"] == "already_released" and "event" not in again
    early = await handle_release(booking["id"])
    assert "event" not in early


async def test_the_sweep_publishes_the_release_event_itself(client, make_user, published):
    lender, borrower = make_user("Lena"), make_user("Ben")
    listing = await create_listing(client, lender)
    booking = (await book(client, borrower, listing["id"], 0, 2)).json()
    await checklist(client, lender, booking["id"], "handover")
    published.events.clear()

    later = datetime.now(UTC) + timedelta(days=8)
    results = await release_due_fees(later)

    assert [r["status"] for r in results] == ["released"]
    assert all("event" not in r for r in results)  # moved out, so callers see plain results
    assert published.types == ["fee.released"]
    assert await release_due_fees(later) == []
    assert published.types == ["fee.released"]  # no second email for the same release


def test_sns_publisher_sends_json_with_a_filterable_type(monkeypatch):
    sent: list[dict] = []
    fake_client = SimpleNamespace(publish=lambda **kwargs: sent.append(kwargs))
    monkeypatch.setattr(
        "boto3.Session", lambda **_: SimpleNamespace(client=lambda *a, **k: fake_client)
    )
    publisher = notifications.SnsPublisher(
        Settings(events_topic_arn="arn:aws:sns:ap-southeast-1:1:events")
    )
    event = {"type": "fee.released", "booking": {"id": "b1"}}

    publisher.publish(event)

    (call,) = sent
    assert call["TopicArn"] == "arn:aws:sns:ap-southeast-1:1:events"
    assert json.loads(call["Message"]) == event
    assert call["MessageAttributes"]["eventType"]["StringValue"] == "fee.released"


def test_sns_backend_needs_a_topic():
    with pytest.raises(RuntimeError, match="PASSIT_EVENTS_TOPIC_ARN"):
        notifications.SnsPublisher(Settings(notifications_backend="sns"))
