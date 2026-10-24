from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import case, func, select

from app.auth.dependencies import CurrentUser
from app.core.db import DbSession
from app.models import Booking, Listing
from app.models import LedgerEntry as LedgerRow
from app.schemas import ApiModel

router = APIRouter(tags=["transactions"])

ZERO = Decimal("0.00")


class LedgerEntry(ApiModel):
    account: Literal["borrower", "lender", "platform_hold"]
    entry_type: Literal[
        "hold_fee", "hold_deposit", "release_fee", "refund_deposit", "damage_payout"
    ]
    amount: Decimal
    created_at: datetime


class Dashboard(ApiModel):
    """Money figures are simulated ledger totals in SGD; no real payments move."""

    role: Literal["borrower", "lender"]
    completed_rentals: int
    active_rentals: int
    earnings: Decimal  # lender: fees released plus damage payouts received
    pending_release: Decimal  # lender: fees still held for non-cancelled bookings
    total_spent: Decimal  # borrower: fees plus damage payouts paid
    deposits_held: Decimal  # borrower: deposits not yet settled
    savings: Decimal  # borrower: estimated saving versus buying (see get_dashboard)


@router.get(
    "/bookings/{booking_id}/ledger",
    response_model=list[LedgerEntry],
    operation_id="getBookingLedger",
)
async def get_booking_ledger(
    booking_id: UUID, user: CurrentUser, db: DbSession
) -> list[LedgerEntry]:
    """Every simulated money movement for a booking; each event sums to zero."""
    row = (
        await db.execute(
            select(Booking.borrower_id, Listing.owner_id)
            .join(Listing, Listing.id == Booking.listing_id)
            .where(Booking.id == booking_id)
        )
    ).first()
    if row is None or user.id not in row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found")
    entries = await db.scalars(
        select(LedgerRow)
        .where(LedgerRow.booking_id == booking_id)
        .order_by(LedgerRow.created_at, LedgerRow.id)
    )
    return [
        LedgerEntry(
            account=e.account, entry_type=e.entry_type, amount=e.amount, created_at=e.created_at
        )
        for e in entries
    ]


def _sum(column) -> object:  # noqa: ANN001 - SQLAlchemy expression helper
    return func.coalesce(func.sum(column), ZERO)


@router.get("/dashboard", response_model=Dashboard, operation_id="getDashboard")
async def get_dashboard(
    user: CurrentUser, db: DbSession, role: Literal["borrower", "lender"] = "borrower"
) -> Dashboard:
    """Aggregates for the borrower (savings) and lender (earnings) dashboards.

    Savings is an estimate: the listing deposit stands in for the item's replacement
    value, so savings = sum(max(deposit - fee, 0)) over non-cancelled rentals.
    """
    party = Booking.borrower_id == user.id if role == "borrower" else Listing.owner_id == user.id
    bookings = (
        select(Booking.id, Booking.state, Booking.fee, Booking.deposit)
        .join(Listing, Listing.id == Booking.listing_id)
        .where(party)
        .subquery()
    )
    saving = func.greatest(bookings.c.deposit - bookings.c.fee, 0)
    counts = (
        await db.execute(
            select(
                func.count().filter(bookings.c.state.in_(("returned", "settled"))),
                func.count().filter(bookings.c.state.in_(("confirmed", "handed_over"))),
                _sum(case((bookings.c.state != "cancelled", saving), else_=0)),
            )
        )
    ).one()

    def ledger_total(account: str, *types: str):  # noqa: ANN202
        return (
            select(_sum(LedgerRow.amount))
            .where(
                LedgerRow.booking_id.in_(select(bookings.c.id)),
                LedgerRow.account == account,
                LedgerRow.entry_type.in_(types),
            )
            .scalar_subquery()
        )

    totals = (
        await db.execute(
            select(
                ledger_total("lender", "release_fee", "damage_payout"),
                ledger_total("platform_hold", "hold_fee", "release_fee"),
                ledger_total("borrower", "hold_fee"),
                ledger_total("lender", "damage_payout"),
                ledger_total("platform_hold", "hold_deposit", "refund_deposit", "damage_payout"),
            )
        )
    ).one()
    earnings, fees_held, borrower_fees, damage_paid, deposits_held = (Decimal(v) for v in totals)
    if role == "lender":
        return Dashboard(
            role=role,
            completed_rentals=counts[0],
            active_rentals=counts[1],
            earnings=earnings,
            pending_release=fees_held,
            total_spent=ZERO,
            deposits_held=ZERO,
            savings=ZERO,
        )
    return Dashboard(
        role=role,
        completed_rentals=counts[0],
        active_rentals=counts[1],
        earnings=ZERO,
        pending_release=ZERO,
        # borrower hold_fee entries are negative; a cancelled hold nets to zero
        total_spent=-borrower_fees + damage_paid,
        deposits_held=deposits_held,
        savings=Decimal(counts[2]),
    )
