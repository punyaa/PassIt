"""Pure Plus plan rules. No I/O, so they can be unit-tested directly.

Saver is free forever and never expires. Paid plans run 30-day periods and are
simulated in the prototype: choosing one records the membership without charging.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

Plan = Literal["saver", "eco-saver", "mega-saver"]

CENT = Decimal("0.01")


@dataclass(frozen=True)
class Perks:
    deposit_factor: Decimal  # share of the listing deposit this plan pays
    free_rescheduling: bool  # cancel-and-rebook before pickup at no cost
    delivery_credits: int  # free deliveries per period
    grace_days: int  # extra days of grace on every return
    listing_limit: int | None  # active listings a lender may have; None = unlimited
    payout_hold_minutes: int | None  # cap on the fee hold after handover; None = default


PLANS: dict[str, Perks] = {
    "saver": Perks(Decimal("1.00"), False, 0, 0, 3, None),
    "eco-saver": Perks(Decimal("0.75"), True, 0, 0, 10, 3 * 24 * 60),
    "mega-saver": Perks(Decimal("0.00"), True, 1, 1, None, 60),
}

PLAN_ORDER = ("saver", "eco-saver", "mega-saver")


def deposit_for(plan: str, listing_deposit: Decimal) -> Decimal:
    """The deposit a booking holds: the plan's share of the listing deposit."""
    return (listing_deposit * PLANS[plan].deposit_factor).quantize(CENT, rounding=ROUND_HALF_UP)


def listing_limit_for(plan: str, free_limit: int) -> int | None:
    """Active listings a lender on this plan may have. Saver uses the configured free
    limit; paid plans never get fewer than that. None means unlimited."""
    if plan == "saver":
        return free_limit
    limit = PLANS[plan].listing_limit
    return None if limit is None else max(limit, free_limit)


def fee_hold_minutes_for(plan: str, default_minutes: int) -> int:
    """How long a lender's rental fee is held after handover. Paid plans release sooner;
    a shorter configured default (e.g. 1 minute on staging) always wins."""
    cap = PLANS[plan].payout_hold_minutes
    return default_minutes if cap is None else min(cap, default_minutes)
