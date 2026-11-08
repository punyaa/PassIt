"""Membership persistence. Every function runs inside the caller's transaction and never
commits, so signup and its membership land together or not at all."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.memberships.plans import PLAN_ORDER
from app.models import Membership, MembershipEvent


def period_end_for(plan: str, start: datetime) -> datetime | None:
    """Saver is free forever and never expires; paid plans run one membership period."""
    if plan == "saver":
        return None
    return start + get_settings().membership_period


async def get_membership(db: AsyncSession, user_id: UUID) -> Membership | None:
    return await db.scalar(select(Membership).where(Membership.user_id == user_id))


async def active_membership(db: AsyncSession, user_id: UUID) -> Membership | None:
    membership = await get_membership(db, user_id)
    if membership is None or membership.status != "active":
        return None
    return membership


async def plan_for(db: AsyncSession, user_id: UUID) -> str:
    """The plan that prices this user's bookings. Users without an active membership
    (pre-membership accounts, expired members) are Saver, which is free forever."""
    membership = await active_membership(db, user_id)
    return membership.plan if membership else "saver"


async def _record_event(
    db: AsyncSession,
    membership: Membership,
    event: str,
    from_plan: str | None = None,
    to_plan: str | None = None,
) -> None:
    db.add(
        MembershipEvent(
            membership_id=membership.id, event=event, from_plan=from_plan, to_plan=to_plan
        )
    )


async def start_membership(
    db: AsyncSession, user_id: UUID, plan: str, *, now: datetime | None = None
) -> Membership:
    """Create the row signup needs. The caller commits."""
    now = now or datetime.now(UTC)
    membership = Membership(
        user_id=user_id,
        plan=plan,
        status="active",
        current_period_start=now,
        current_period_end=period_end_for(plan, now),
    )
    db.add(membership)
    await db.flush()
    await _record_event(db, membership, "created", to_plan=plan)
    return membership


async def change_plan(
    db: AsyncSession, user_id: UUID, plan: str, *, now: datetime | None = None
) -> Membership:
    """Choose a plan. Simulated: no charge, the new period starts immediately. Creates
    the row for pre-membership users; reactivates expired ones."""
    now = now or datetime.now(UTC)
    membership = await db.scalar(
        select(Membership).where(Membership.user_id == user_id).with_for_update()
    )
    if membership is None:
        return await start_membership(db, user_id, plan, now=now)
    if membership.plan == plan and membership.status == "active":
        return membership  # same plan: keep the current period
    from_plan = membership.plan
    membership.plan = plan
    membership.status = "active"
    membership.current_period_start = now
    membership.current_period_end = period_end_for(plan, now)
    membership.updated_at = now
    event = "upgraded" if PLAN_ORDER.index(plan) > PLAN_ORDER.index(from_plan) else "downgraded"
    await _record_event(db, membership, event, from_plan=from_plan, to_plan=plan)
    return membership
