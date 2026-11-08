"""The mailer Lambda: reading events off SNS and turning them into emails."""

import json

import pytest

from tests.lambda_modules import load


@pytest.fixture
def mailer(monkeypatch):
    return load(
        "mailer",
        monkeypatch,
        SEND_EMAILS="true",
        SENDER="PassIt <noreply@passit.test.org>",
        COPY_TO="team@school.edu",
        SITE_URL="https://site.example.org/",
        SKIP_DOMAINS="passit.demo,example.com",
    )


class FakeSes:
    def __init__(self, fail_for: str | None = None) -> None:
        self.sent: list[dict] = []
        self.fail_for = fail_for

    def send_email(self, **kwargs):
        if self.fail_for and self.fail_for in kwargs["Destination"]["ToAddresses"]:
            raise RuntimeError("MessageRejected: Email address is not verified")
        self.sent.append(kwargs)


def event(kind: str, **booking) -> dict:
    return {
        "event_id": "e1",
        "version": 1,
        "type": kind,
        "occurred_at": "2026-11-01T10:00:00+00:00",
        "actor": "borrower",
        "booking": {
            "id": "b-123",
            "listing_id": "l-1",
            "listing_title": "Camping tent",
            "start_date": "2026-11-06",
            "end_date": "2026-11-08",
            "duration_type": "day",
            "fee": "36.00",
            "deposit": "80.00",
            "state": "confirmed",
            "damage_severity": None,
            "fee_release_at": "2026-11-09T10:00:00+00:00",
            **booking,
        },
        "borrower": {"name": "Ben", "email": "ben@school.edu"},
        "lender": {"name": "Lena", "email": "lena@school.edu"},
    }


def sns(message: dict | str) -> dict:
    body = message if isinstance(message, str) else json.dumps(message)
    return {"Records": [{"Sns": {"Message": body}}]}


def test_a_published_event_is_read_as_it_is(mailer):
    assert mailer.extract_events(sns(event("booking.confirmed"))) == [event("booking.confirmed")]


def test_the_release_event_is_found_inside_a_lambda_destination_record(mailer):
    record = {
        "version": "1.0",
        "requestPayload": {"booking_id": "b-123"},
        "responsePayload": {
            "booking_id": "b-123",
            "status": "released",
            "event": event("fee.released"),
        },
    }
    assert mailer.extract_events(sns(record)) == [event("fee.released")]


@pytest.mark.parametrize(
    "message",
    [
        {"responsePayload": {"booking_id": "b-123", "status": "already_released"}},
        {"responsePayload": None},
        {"something": "else"},
        "not json at all {",
        "[1, 2]",
    ],
)
def test_messages_without_an_event_send_nothing(mailer, message):
    assert mailer.extract_events(sns(message)) == []


@pytest.mark.parametrize(
    "kind,who",
    [
        ("booking.confirmed", {"ben@school.edu", "lena@school.edu"}),
        ("booking.handed_over", {"ben@school.edu", "lena@school.edu"}),
        ("booking.returned", {"ben@school.edu", "lena@school.edu"}),
        ("booking.settled", {"ben@school.edu", "lena@school.edu"}),
        ("booking.cancelled", {"ben@school.edu", "lena@school.edu"}),
        ("fee.released", {"lena@school.edu"}),  # only the lender is paid
    ],
)
def test_each_event_goes_to_the_people_it_concerns(mailer, kind, who):
    mails = mailer.render(event(kind))
    assert {m.to for m in mails} == who
    assert all("Camping tent" in m.subject or "S$36.00" in m.subject for m in mails)


def test_a_damage_claim_says_what_share_of_the_deposit_moved(mailer):
    mails = mailer.render(event("booking.settled", damage_severity="severe"))
    text = " ".join(" ".join(m.paragraphs) for m in mails)
    assert "70%" in text and "severe" in text
    clean = mailer.render(event("booking.settled", damage_severity="none"))
    assert any("refunded in full" in " ".join(m.paragraphs) for m in clean)


def test_the_email_links_to_the_booking_and_has_text_and_html(mailer):
    (mail,) = mailer.render(event("fee.released"))
    text, page = mailer._body(mail)
    assert "https://site.example.org/bookings/b-123" in text
    assert 'href="https://site.example.org/bookings/b-123"' in page
    assert "payments are simulated" in text


def test_user_supplied_text_cannot_inject_html_or_headers(mailer):
    nasty = event(
        "booking.confirmed", listing_title="<script>alert(1)</script>\r\nBcc: attacker@evil.example"
    )
    mails = mailer.render(nasty)
    assert all("\n" not in m.subject and "\r" not in m.subject for m in mails)
    _, page = mailer._body(mails[0])
    assert "<script>" not in page and "&lt;script&gt;" in page


def test_every_email_is_copied_to_the_team_and_sent_from_the_sender(mailer, monkeypatch):
    ses = FakeSes()
    monkeypatch.setattr(mailer, "_ses", lambda: ses)

    result = mailer.handler(sns(event("booking.confirmed")))

    assert result == {"sent": 2, "not_sent": 0}
    first = ses.sent[0]
    assert first["FromEmailAddress"] == "PassIt <noreply@passit.test.org>"
    assert first["Destination"]["ToAddresses"] == ["ben@school.edu"]
    assert first["Destination"]["BccAddresses"] == ["team@school.edu"]
    assert (
        "Text" in first["Content"]["Simple"]["Body"]
        and "Html" in first["Content"]["Simple"]["Body"]
    )


def test_the_team_address_is_not_copied_on_its_own_email(mailer, monkeypatch):
    ses = FakeSes()
    monkeypatch.setattr(mailer, "_ses", lambda: ses)
    data = event("fee.released")
    data["lender"]["email"] = "Team@School.edu"
    mailer.handler(sns(data))
    assert "BccAddresses" not in ses.sent[0]["Destination"]


def test_seed_and_example_addresses_are_never_emailed(mailer, monkeypatch):
    ses = FakeSes()
    monkeypatch.setattr(mailer, "_ses", lambda: ses)
    data = event("booking.confirmed")
    data["borrower"]["email"] = "seed-01@passit.demo"
    data["lender"]["email"] = "someone@sub.example.com"
    assert mailer.handler(sns(data)) == {"sent": 0, "not_sent": 2}
    assert ses.sent == []
    assert mailer._allowed("a@notexample.com")  # only the domain or its subdomains are skipped
    assert not mailer._allowed("no-at-sign")


def test_ses_refusing_one_address_does_not_stop_the_others(mailer, monkeypatch):
    ses = FakeSes(fail_for="ben@school.edu")  # e.g. not verified while SES is in the sandbox
    monkeypatch.setattr(mailer, "_ses", lambda: ses)
    result = mailer.handler(sns(event("booking.confirmed")))
    assert result == {"sent": 1, "not_sent": 1}
    assert ses.sent[0]["Destination"]["ToAddresses"] == ["lena@school.edu"]


@pytest.mark.parametrize("setting", [None, "", "false", "no", "0"])
def test_the_feature_is_off_unless_explicitly_switched_on(monkeypatch, setting):
    env = {"SENDER": "x@school.edu"} | ({} if setting is None else {"SEND_EMAILS": setting})
    monkeypatch.delenv("SEND_EMAILS", raising=False)
    off = load("mailer", monkeypatch, **env)
    ses = FakeSes()
    monkeypatch.setattr(off, "_ses", lambda: ses)

    assert off.handler(sns(event("booking.confirmed"))) == {"sent": 0, "not_sent": 0}
    assert ses.sent == []  # not even attempted
