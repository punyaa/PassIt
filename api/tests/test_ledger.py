"""B2 ledger invariants. The property test drives random action sequences through the
same state machine and entry builders the API uses."""

from decimal import Decimal

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.bookings.state_machine import ACTIONS, can_transition
from app.transactions.ledger import (
    DAMAGE_TIERS,
    Entry,
    account_balances,
    balanced_entries,
    cancel_entries,
    damage_split,
    hold_entries,
    release_fee_entries,
    settle_deposit_entries,
)

ZERO = Decimal("0.00")


def test_booking_hold_balances_to_zero() -> None:
    entries = hold_entries(Decimal("50.00"), Decimal("80.00"))
    assert sum((entry.amount for entry in entries), start=ZERO) == ZERO


def test_unbalanced_event_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unbalanced ledger"):
        balanced_entries([Entry("borrower", "hold_fee", Decimal("-50.00"))])


@pytest.mark.parametrize(
    ("severity", "payout"),
    [
        ("none", "0.00"),
        ("minor", "16.00"),
        ("moderate", "32.00"),
        ("severe", "56.00"),
        ("total", "80.00"),
    ],
)
def test_damage_tiers(severity: str, payout: str) -> None:
    paid, refund = damage_split(Decimal("80.00"), severity)
    assert paid == Decimal(payout) and paid + refund == Decimal("80.00")


def test_odd_cent_damage_split_still_balances() -> None:
    paid, refund = damage_split(Decimal("33.33"), "minor")
    assert paid + refund == Decimal("33.33")
    assert sum(e.amount for e in settle_deposit_entries(Decimal("33.33"), "minor")) == ZERO


class Simulation:
    """Mirror of the API's guarded transitions, applied to an in-memory ledger."""

    def __init__(self, fee: Decimal, deposit: Decimal) -> None:
        self.fee, self.deposit = fee, deposit
        self.state: str | None = None
        self.entries: list[Entry] = []
        self.released = False

    def post(self, entries: list[Entry]) -> None:
        assert sum((e.amount for e in entries), start=ZERO) == ZERO
        self.entries += entries

    def apply(self, action: str, severity: str) -> None:
        if action == "book":
            if self.state is None:
                self.state = "confirmed"
                self.post(hold_entries(self.fee, self.deposit))
            return
        if action == "release":  # idempotent scheduled release
            if self.state in ("handed_over", "returned", "settled") and not self.released:
                self.post(release_fee_entries(self.fee))
                self.released = True
            return
        from_state, _ = ACTIONS[action]
        if self.state != from_state:
            return  # the API answers 409 and writes nothing
        target = {
            "handover": "handed_over",
            "cancel": "cancelled",
            "return": "returned",
            "settle": "settled",
            "report_damage": "settled",
        }[action]
        assert can_transition(self.state, target)
        if action == "cancel":
            self.post(cancel_entries(self.fee, self.deposit))
        elif action == "settle":
            self.post(settle_deposit_entries(self.deposit, "none"))
        elif action == "report_damage":
            self.post(settle_deposit_entries(self.deposit, severity))
        self.state = target


money = st.decimals(min_value="0.00", max_value="5000.00", places=2)


@settings(max_examples=300)
@given(
    fee=money.filter(lambda value: value > 0),
    deposit=money,
    actions=st.lists(
        st.tuples(
            st.sampled_from(
                ["book", "handover", "release", "return", "settle", "report_damage", "cancel"]
            ),
            st.sampled_from(sorted(DAMAGE_TIERS)),
        ),
        max_size=12,
    ),
)
def test_ledger_always_balances(fee, deposit, actions) -> None:
    sim = Simulation(fee, deposit)
    for action, severity in actions:
        sim.apply(action, severity)
        balances = account_balances(sim.entries)
        assert sum(balances.values(), start=ZERO) == ZERO
        assert balances["platform_hold"] >= ZERO  # never pays out money it does not hold
        assert balances["lender"] >= ZERO
    finished = sim.state == "cancelled" or (sim.state == "settled" and sim.released)
    if finished:
        assert account_balances(sim.entries)["platform_hold"] == ZERO
