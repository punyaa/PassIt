from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Entry:
    account: str
    entry_type: str
    amount: Decimal


def balanced_entries(entries: list[Entry]) -> list[Entry]:
    total = sum((entry.amount for entry in entries), start=Decimal("0.00"))
    if total != Decimal("0.00"):
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
