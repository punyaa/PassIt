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


PLANS: dict[str, Perks] = {
    "saver": Perks(Decimal("1.00"), False, 0, 0),
    "eco-saver": Perks(Decimal("0.75"), True, 0, 0),
    "mega-saver": Perks(Decimal("0.00"), True, 1, 1),
}

PLAN_ORDER = ("saver", "eco-saver", "mega-saver")


def deposit_for(plan: str, listing_deposit: Decimal) -> Decimal:
    """The deposit a booking holds: the plan's share of the listing deposit."""
    return (listing_deposit * PLANS[plan].deposit_factor).quantize(CENT, rounding=ROUND_HALF_UP)
