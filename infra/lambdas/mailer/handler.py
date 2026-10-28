"""Turns booking and release events into emails, sent with Amazon SES.

Subscribed to the events SNS topic. Two kinds of message arrive there:

- A booking event published by the API (`booking.confirmed`, `booking.handed_over`,
  `booking.returned`, `booking.settled`, `booking.cancelled`).
- The result of the fee-release Lambda, wrapped in an invocation record by a Lambda
  destination. The `fee.released` event is inside it, under `responsePayload.event`. A result
  with no event (nothing was released) sends nothing.

The event format is documented in api/app/notifications/events.py. Each event goes to the
people it concerns, borrower and lender, and every email is also copied (Bcc) to COPY_TO.

Settings, from environment variables set by Terraform:
  SEND_EMAILS   "true" to send. Anything else, or unset, switches the feature off: events are
                received and ignored, and nothing is sent. This is the on/off switch.
  SENDER        the verified SES address emails come from (required when sending)
  COPY_TO       comma-separated addresses that receive a copy of every email
  SITE_URL      the site's address, used for the link in each email
  SKIP_DOMAINS  recipient domains never emailed: the seed accounts, tests and examples

SES starts in "sandbox" mode, where it only delivers to addresses that have been verified
(Terraform creates and verifies identities for the addresses it is given). A send that SES
refuses is logged and skipped, never retried, so one bad address cannot hold up the others.
"""

import html
import json
import logging
import os
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ENABLED = os.environ.get("SEND_EMAILS", "").strip().lower() == "true"
SENDER = os.environ.get("SENDER", "")
COPY_TO = [a.strip() for a in os.environ.get("COPY_TO", "").split(",") if a.strip()]
SITE_URL = os.environ.get("SITE_URL", "").rstrip("/")
SKIP_DOMAINS = tuple(
    d.strip().lower()
    for d in os.environ.get(
        "SKIP_DOMAINS", "passit.demo,example.com,example.org,example.net"
    ).split(",")
    if d.strip()
)

# Share of the deposit that goes to the lender, by damage tier (fixed by the backend).
DAMAGE_SHARE = {"minor": "20%", "moderate": "40%", "severe": "70%", "total": "100%"}

_client: Any = None


def _ses() -> Any:
    global _client
    if _client is None:
        import boto3  # noqa: PLC0415 - provided by the Lambda runtime

        _client = boto3.client("sesv2")
    return _client


@dataclass(frozen=True)
class Mail:
    to: str
    subject: str
    paragraphs: list[str]
    link: str | None


def _clean(text: str) -> str:
    """No line breaks in a value that ends up in a header."""
    return " ".join(str(text).split())


def _money(value: str) -> str:
    return f"S${value}"


def _dates(booking: dict[str, Any]) -> str:
    start, end = booking["start_date"], booking["end_date"]
    return start if start == end else f"{start} to {end}"


def extract_events(lambda_event: dict[str, Any]) -> list[dict[str, Any]]:
    events = []
    for record in lambda_event.get("Records", []):
        try:
            message = json.loads(record["Sns"]["Message"])
        except (KeyError, ValueError):
            logger.warning("ignoring a message that is not JSON")
            continue
        if not isinstance(message, dict):
            continue
        # A Lambda destination wraps the function's result; a published event is bare.
        wrapped = message.get("responsePayload")
        candidate = wrapped.get("event") if isinstance(wrapped, dict) else message
        if isinstance(candidate, dict) and "type" in candidate and "booking" in candidate:
            events.append(candidate)
    return events


def render(event: dict[str, Any]) -> list[Mail]:
    """The emails one event produces, one per person it concerns."""
    kind = event["type"]
    booking, borrower, lender = event["booking"], event["borrower"], event["lender"]
    title = _clean(booking["listing_title"])
    link = f"{SITE_URL}/bookings/{booking['id']}" if SITE_URL else None
    when = _dates(booking)
    fee, deposit = _money(booking["fee"]), _money(booking["deposit"])
    b_name, l_name = _clean(borrower["name"]), _clean(lender["name"])

    def to_borrower(subject: str, *paragraphs: str) -> Mail:
        return Mail(borrower["email"], subject, [f"Hi {b_name},", *paragraphs], link)

    def to_lender(subject: str, *paragraphs: str) -> Mail:
        return Mail(lender["email"], subject, [f"Hi {l_name},", *paragraphs], link)

    if kind == "booking.confirmed":
        return [
            to_borrower(
                f"Booking confirmed: {title}",
                f"Your booking of {title} for {when} is confirmed.",
                f"PassIt is holding the rental fee ({fee}) and the refundable deposit "
                f"({deposit}). Meet {l_name} to collect the item and complete the handover "
                "checklist.",
            ),
            to_lender(
                f"New booking: {title}",
                f"{b_name} booked {title} for {when}.",
                "Complete the handover checklist, with a photo, when you meet.",
            ),
        ]
    if kind == "booking.handed_over":
        release = booking.get("fee_release_at") or "after the hold period"
        return [
            to_borrower(
                f"Handover recorded: {title}",
                f"The handover of {title} is recorded. Please return it by {booking['end_date']}.",
            ),
            to_lender(
                f"Handover recorded: {title}",
                f"The handover of {title} to {b_name} is recorded.",
                f"The rental fee ({fee}) is released to you at {release}.",
            ),
        ]
    if kind == "booking.returned":
        return [
            to_lender(
                f"Returned, please settle: {title}",
                f"{b_name} has returned {title}.",
                "Check its condition, then refund the deposit or report damage.",
            ),
            to_borrower(
                f"Return recorded: {title}",
                f"Your return of {title} is recorded. {l_name} will check it and settle "
                "your deposit.",
            ),
        ]
    if kind == "booking.settled":
        severity = booking.get("damage_severity") or "none"
        if severity == "none":
            return [
                to_borrower(
                    f"Deposit refunded: {title}",
                    f"{l_name} confirmed {title} came back fine, so your deposit ({deposit}) "
                    "is refunded in full.",
                ),
                to_lender(f"Booking settled: {title}", f"{title} is settled with no damage."),
            ]
        share = DAMAGE_SHARE.get(severity, "part")
        return [
            to_borrower(
                f"Deposit settled with a damage claim: {title}",
                f"{l_name} reported {severity} damage to {title}, so {share} of your deposit "
                f"({deposit}) goes to the lender and the rest is refunded.",
            ),
            to_lender(
                f"Damage claim recorded: {title}",
                f"Your {severity} damage report for {title} is recorded. {share} of the "
                f"deposit ({deposit}) goes to you.",
            ),
        ]
    if kind == "booking.cancelled":
        who = b_name if event.get("actor") == "borrower" else l_name
        text = (
            f"The booking of {title} for {when} was cancelled by {who}. "
            "The fee and deposit are refunded."
        )
        return [
            to_borrower(f"Booking cancelled: {title}", text),
            to_lender(f"Booking cancelled: {title}", text),
        ]
    if kind == "fee.released":
        return [
            to_lender(
                f"Rental fee released: {fee}",
                f"The rental fee of {fee} for {title} has been released to you.",
            )
        ]
    logger.warning("no template for event type %s", kind)
    return []


def _body(mail: Mail) -> tuple[str, str]:
    footer = "PassIt is a prototype: payments are simulated."
    text = "\n\n".join(mail.paragraphs)
    if mail.link:
        text += f"\n\nOpen the booking: {mail.link}"
    text += f"\n\n{footer}\n"
    paragraphs = "".join(f"<p>{html.escape(p)}</p>" for p in mail.paragraphs)
    button = (
        f'<p><a href="{html.escape(mail.link, quote=True)}">Open the booking</a></p>'
        if mail.link
        else ""
    )
    page = (
        f'<div style="font-family:sans-serif">{paragraphs}{button}'
        f"<p><small>{footer}</small></p></div>"
    )
    return text, page


def _allowed(address: str) -> bool:
    if "@" not in address:
        return False
    domain = address.rsplit("@", 1)[1].lower()
    return not any(domain == d or domain.endswith(f".{d}") for d in SKIP_DOMAINS)


def send(mail: Mail) -> bool:
    if not _allowed(mail.to):
        logger.info("skipping %s", mail.subject)
        return False
    text, page = _body(mail)
    destination: dict[str, Any] = {"ToAddresses": [mail.to]}
    copies = [a for a in COPY_TO if a.lower() != mail.to.lower()]
    if copies:
        destination["BccAddresses"] = copies
    try:
        _ses().send_email(
            FromEmailAddress=SENDER,
            Destination=destination,
            Content={
                "Simple": {
                    "Subject": {"Data": _clean(mail.subject), "Charset": "UTF-8"},
                    "Body": {
                        "Text": {"Data": text, "Charset": "UTF-8"},
                        "Html": {"Data": page, "Charset": "UTF-8"},
                    },
                }
            },
        )
    except Exception as error:  # SES refused it (often: sandbox, address not verified)
        logger.error("could not send %r: %s", mail.subject, error)
        return False
    logger.info("sent %r", mail.subject)
    return True


def handler(event: dict[str, Any], context: Any = None) -> dict[str, int]:
    if not ENABLED:
        logger.info("emails are switched off (SEND_EMAILS is not true), ignoring the event")
        return {"sent": 0, "not_sent": 0}
    sent = failed = 0
    for item in extract_events(event):
        for mail in render(item):
            if send(mail):
                sent += 1
            else:
                failed += 1
    return {"sent": sent, "not_sent": failed}
