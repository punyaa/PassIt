import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.auth.dependencies import CurrentUser
from app.core.config import get_settings
from app.core.db import DbSession
from app.integrations.scheduler import get_scheduler
from app.memberships import service
from app.memberships.plans import PLANS, Plan, fee_hold_minutes_for, listing_limit_for
from app.models import Membership
from app.schemas import ApiModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/memberships", tags=["memberships"])


class PerksResponse(ApiModel):
    deposit_factor: Decimal
    free_rescheduling: bool
    delivery_credits: int
    grace_days: int
    listing_limit: int | None  # None = unlimited
    payout_hold_minutes: int


class MembershipResponse(ApiModel):
    user_id: UUID
    plan: Plan
    status: str
    current_period_start: datetime
    current_period_end: datetime | None
    perks: PerksResponse


class MembershipChange(ApiModel):
    plan: Plan


def _to_response(membership: Membership) -> MembershipResponse:
    perks = PLANS[membership.plan]
    settings = get_settings()
    return MembershipResponse(
        user_id=membership.user_id,
        plan=membership.plan,
        status=membership.status,
        current_period_start=membership.current_period_start,
        current_period_end=membership.current_period_end,
        perks=PerksResponse(
            deposit_factor=perks.deposit_factor,
            free_rescheduling=perks.free_rescheduling,
            delivery_credits=perks.delivery_credits,
            grace_days=perks.grace_days,
            listing_limit=listing_limit_for(membership.plan, settings.free_listing_limit),
            payout_hold_minutes=fee_hold_minutes_for(membership.plan, settings.fee_hold_minutes),
        ),
    )


@router.get("/me", response_model=MembershipResponse, operation_id="getMyMembership")
async def get_my_membership(user: CurrentUser, db: DbSession) -> MembershipResponse:
    """The caller's Plus membership. 404 for pre-membership accounts, which are Saver."""
    membership = await service.get_membership(db, user.id)
    if membership is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No membership yet")
    return _to_response(membership)


@router.post("/me", response_model=MembershipResponse, operation_id="setMyMembership")
async def set_my_membership(
    payload: MembershipChange, user: CurrentUser, db: DbSession
) -> MembershipResponse:
    """Choose a plan. Simulated: no charge, the new period starts immediately."""
    try:
        membership = await service.change_plan(db, user.id, payload.plan)
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Membership changed concurrently; try again"
        ) from error
    if membership.current_period_end is not None:
        try:
            # After commit: a rolled-back change must never leave a live schedule behind.
            await asyncio.to_thread(
                get_scheduler().schedule_membership_expiry,
                membership.id,
                membership.current_period_end,
            )
        except Exception:  # the expiry sweep is the safety net
            logger.exception("could not schedule membership expiry for %s", membership.id)
    return _to_response(membership)
