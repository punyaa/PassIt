from decimal import Decimal

import pytest

from app.transactions.ledger import Entry, balanced_entries, hold_entries


def test_booking_hold_balances_to_zero() -> None:
    entries = hold_entries(Decimal("50.00"), Decimal("80.00"))
    assert sum((entry.amount for entry in entries), start=Decimal("0.00")) == Decimal("0.00")


def test_unbalanced_event_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unbalanced ledger"):
        balanced_entries([Entry("borrower", "hold_fee", Decimal("-50.00"))])
