"""Pure double-entry rules. No I/O, so they can be property-tested directly.

Accounts: borrower, lender, platform_hold. Every event's entries sum to zero; over a
booking's life platform_hold returns to zero once the fee is released and the deposit
settled (or the booking is cancelled).

Cancellation reverses the hold with the same entry types and opposite signs, which keeps
the Day 2 ledger_type enum unchanged.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")
ZERO = Decimal("0.00")

# Damage tiers are a lookup, never free input.
DAMAGE_TIERS: dict[str, Decimal] = {
    "none": Decimal("0.00"),
    "minor": Decimal("0.20"),
    "moderate": Decimal("0.40"),
    "severe": Decimal("0.70"),
    "total": Decimal("1.00"),
}


@dataclass(frozen=True)
class Entry:
    account: str
    entry_type: str
    amount: Decimal


def balanced_entries(entries: list[Entry]) -> list[Entry]:
    total = sum((entry.amount for entry in entries), start=ZERO)
    if total != ZERO:
        raise ValueError(f"Unbalanced ledger event: {total}")
    return entries


def hold_entries(fee: Decimal, deposit: Decimal) -> list[Entry]:
    return balanced_entries(
        [
            Entry("borrower", "hold_fee", -fee),
            Entry("platform_hold", "hold_fee", fee),
            Entry("borrower", "hold_deposit", -deposit),
            Entry("platform_hold", "hold_deposit", deposit),
        ]
    )


def cancel_entries(fee: Decimal, deposit: Decimal) -> list[Entry]:
    """Reverse both holds in full."""
    return balanced_entries(
        [
            Entry("platform_hold", "hold_fee", -fee),
            Entry("borrower", "hold_fee", fee),
            Entry("platform_hold", "hold_deposit", -deposit),
            Entry("borrower", "hold_deposit", deposit),
        ]
    )


def release_fee_entries(fee: Decimal) -> list[Entry]:
    return balanced_entries(
        [
            Entry("platform_hold", "release_fee", -fee),
            Entry("lender", "release_fee", fee),
        ]
    )


def damage_split(deposit: Decimal, severity: str) -> tuple[Decimal, Decimal]:
    """Return (payout to lender, refund to borrower); they always add up to the deposit."""
    if severity not in DAMAGE_TIERS:
        raise ValueError(f"Unknown damage severity: {severity}")
    payout = (deposit * DAMAGE_TIERS[severity]).quantize(CENT, rounding=ROUND_HALF_UP)
    return payout, deposit - payout


def settle_deposit_entries(deposit: Decimal, severity: str) -> list[Entry]:
    """Release the deposit hold: pay the damage share to the lender, refund the rest."""
    payout, refund = damage_split(deposit, severity)
    entries = []
    if payout:
        entries += [
            Entry("platform_hold", "damage_payout", -payout),
            Entry("lender", "damage_payout", payout),
        ]
    if refund or not payout:  # a zero deposit still records that settlement happened
        entries += [
            Entry("platform_hold", "refund_deposit", -refund),
            Entry("borrower", "refund_deposit", refund),
        ]
    return balanced_entries(entries)


def account_balances(entries: list[Entry]) -> dict[str, Decimal]:
    balances = {"borrower": ZERO, "lender": ZERO, "platform_hold": ZERO}
    for entry in entries:
        balances[entry.account] += entry.amount
    return balances
