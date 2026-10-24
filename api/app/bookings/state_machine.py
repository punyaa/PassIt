"""Booking lifecycle. Pure rules; the router applies them under a row lock.

    confirmed --handover--> handed_over --return--> returned --settle/damage--> settled
        \\--cancel--> cancelled

Bookings are created directly as `confirmed` (instant booking) so the exclusion
constraint guards the dates from the first insert. `requested` stays in the enum for a
future request-to-book flow. `disputed` is reserved for an admin review flow: nothing
enters it yet, but fee release already refuses to pay out while a booking is disputed.

`settled` means the deposit has been settled. The rental fee is released separately,
`fee_hold_minutes` after handover, by the scheduler (see app/transactions/release.py).
"""

from typing import Literal

from fastapi import HTTPException, status

Role = Literal["borrower", "lender"]

TRANSITIONS: dict[str, set[str]] = {
    "requested": {"confirmed", "cancelled"},
    "confirmed": {"handed_over", "cancelled"},
    "handed_over": {"returned", "disputed"},
    "returned": {"settled", "disputed"},
    "disputed": {"settled"},
    "settled": set(),
    "cancelled": set(),
}

# Which party may perform each action, and from which state.
ACTIONS: dict[str, tuple[str, set[Role]]] = {
    "handover": ("confirmed", {"borrower", "lender"}),
    "cancel": ("confirmed", {"borrower", "lender"}),
    "return": ("handed_over", {"borrower", "lender"}),
    "settle": ("returned", {"lender"}),
    "report_damage": ("returned", {"lender"}),
}

REVIEWABLE_STATES = {"returned", "settled"}


def can_transition(current: str, target: str) -> bool:
    return target in TRANSITIONS.get(current, set())


def require_action(action: str, current_state: str, role: Role) -> None:
    """Raise 409 for a wrong state and 403 for the wrong party."""
    from_state, roles = ACTIONS[action]
    if current_state != from_state:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Cannot {action.replace('_', ' ')} a booking that is {current_state}",
        )
    if role not in roles:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, f"Only the {' or '.join(roles)} can {action}"
        )


def available_actions(state: str, role: Role, has_reviewed: bool) -> list[str]:
    actions = [
        action
        for action, (from_state, roles) in ACTIONS.items()
        if from_state == state and role in roles
    ]
    if state in REVIEWABLE_STATES and not has_reviewed:
        actions.append("review")
    return actions
