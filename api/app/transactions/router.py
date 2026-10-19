from decimal import Decimal
from typing import Literal
from uuid import UUID

from fastapi import APIRouter

from app.core.stubs import not_implemented
from app.schemas import ApiModel

router = APIRouter(tags=["transactions"])


class LedgerEntry(ApiModel):
    account: Literal["borrower", "lender", "platform_hold"]
    entry_type: Literal[
        "hold_fee", "hold_deposit", "release_fee", "refund_deposit", "damage_payout"
    ]
    amount: Decimal


class Dashboard(ApiModel):
    role: Literal["borrower", "lender"]
    completed_rentals: int
    earnings: Decimal
    savings: Decimal


@router.get(
    "/bookings/{booking_id}/ledger",
    response_model=list[LedgerEntry],
    operation_id="getBookingLedger",
)
async def get_booking_ledger(booking_id: UUID) -> list[LedgerEntry]:
    not_implemented(f"ledger for {booking_id}", "B2 Transactions")


@router.get("/dashboard", response_model=Dashboard, operation_id="getDashboard")
async def get_dashboard() -> Dashboard:
    not_implemented("dashboard aggregation", "B2 Transactions")
