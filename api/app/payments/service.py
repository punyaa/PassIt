"""Translate booking lifecycle events into gateway operations."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import Booking
from app.payments.gateway import PaymentGateway
from app.payments.mock import MockPaymentGateway
from app.transactions.ledger import damage_split


def get_payment_gateway() -> PaymentGateway:
    mode = get_settings().payment_mode
    if mode == "mock":
        return MockPaymentGateway()
    raise RuntimeError(f"Unsupported payment mode: {mode}")


async def collect_booking_payment(
    db: AsyncSession, booking: Booking, payment_method: str
) -> None:
    await get_payment_gateway().collect(
        db,
        booking_id=booking.id,
        amount=booking.fee + booking.deposit,
        payment_method=payment_method,
        idempotency_key=f"booking:{booking.id}:collect",
    )


async def refund_cancelled_booking(db: AsyncSession, booking: Booking) -> None:
    await get_payment_gateway().refund(
        db,
        booking_id=booking.id,
        amount=booking.fee + booking.deposit,
        idempotency_key=f"booking:{booking.id}:cancel-refund",
    )


async def payout_fee(
    db: AsyncSession, booking: Booking, lender_id: UUID
) -> None:
    await get_payment_gateway().payout(
        db,
        booking_id=booking.id,
        recipient_id=lender_id,
        amount=booking.fee,
        idempotency_key=f"booking:{booking.id}:fee-payout",
    )


async def settle_deposit(
    db: AsyncSession, booking: Booking, lender_id: UUID, severity: str
) -> None:
    payout, refund = damage_split(booking.deposit, severity)
    gateway = get_payment_gateway()
    if refund > Decimal("0"):
        await gateway.refund(
            db,
            booking_id=booking.id,
            amount=refund,
            idempotency_key=f"booking:{booking.id}:deposit-refund",
        )
    if payout > Decimal("0"):
        await gateway.payout(
            db,
            booking_id=booking.id,
            recipient_id=lender_id,
            amount=payout,
            idempotency_key=f"booking:{booking.id}:damage-payout",
        )
