"""Scheduled membership expiry. Safe to run any number of times for the same member."""

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select

from app.core.db import get_sessionmaker
from app.models import Membership, MembershipEvent

logger = logging.getLogger(__name__)


async def handle_expiry(membership_id: UUID | str, now: datetime | None = None) -> dict[str, str]:
    """Expire a lapsed paid membership. Expired members fall back to free Saver, so
    expiry only flips the status and records the event; nothing else changes.

    EventBridge may deliver more than once and the local sweep may race it; the row
    lock plus the status check make every extra call a no-op.
    """
    membership_id = UUID(str(membership_id))
    now = now or datetime.now(UTC)
    async with get_sessionmaker()() as db, db.begin():
        membership = await db.get(Membership, membership_id, with_for_update=True)
        if membership is None:
            status = "not_found"
        elif membership.status != "active":
            status = "already_expired"
        elif membership.current_period_end is None or membership.current_period_end > now:
            status = "not_due"
        else:
            from_plan = membership.plan
            membership.status = "expired"
            membership.updated_at = now
            db.add(
                MembershipEvent(
                    membership_id=membership.id,
                    event="expired",
                    from_plan=from_plan,
                    to_plan="saver",
                )
            )
            status = "expired"
    logger.info("membership expiry %s: %s", membership_id, status)
    return {"membership_id": str(membership_id), "status": status}


async def expire_due_memberships(now: datetime | None = None) -> list[dict[str, str]]:
    """Expire every active membership whose period has ended."""
    now = now or datetime.now(UTC)
    async with get_sessionmaker()() as db:
        due = await db.scalars(
            select(Membership.id).where(
                Membership.status == "active",
                Membership.current_period_end <= now,
            )
        )
        membership_ids = list(due)
    return [await handle_expiry(membership_id, now) for membership_id in membership_ids]
