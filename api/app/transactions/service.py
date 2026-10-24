"""Ledger persistence. Every function runs inside the caller's transaction and never
commits, so a booking state change and its ledger entries land together or not at all.

`hold_funds(db, booking)` is the Day 2 signature B1 calls from create_booking.
"""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Booking, LedgerEntry
from app.transactions import ledger


async def post_entries(db: AsyncSession, booking_id: UUID, entries: list[ledger.Entry]) -> None:
    for entry in ledger.balanced_entries(entries):
        db.add(
            LedgerEntry(
                booking_id=booking_id,
                account=entry.account,
                entry_type=entry.entry_type,
                amount=entry.amount,
            )
        )
    await db.flush()


async def hold_funds(db: AsyncSession, booking: Booking) -> None:
    await post_entries(db, booking.id, ledger.hold_entries(booking.fee, booking.deposit))


async def reverse_holds(db: AsyncSession, booking: Booking) -> None:
    await post_entries(db, booking.id, ledger.cancel_entries(booking.fee, booking.deposit))


async def release_fee(db: AsyncSession, booking: Booking) -> None:
    await post_entries(db, booking.id, ledger.release_fee_entries(booking.fee))


async def settle_deposit(db: AsyncSession, booking: Booking, severity: str) -> None:
    await post_entries(db, booking.id, ledger.settle_deposit_entries(booking.deposit, severity))


async def has_entry(db: AsyncSession, booking_id: UUID, *entry_types: str) -> bool:
    return bool(
        await db.scalar(
            select(
                exists().where(
                    LedgerEntry.booking_id == booking_id,
                    LedgerEntry.entry_type.in_(entry_types),
                )
            )
        )
    )


async def fee_released(db: AsyncSession, booking_id: UUID) -> bool:
    return await has_entry(db, booking_id, "release_fee")


async def deposit_settled(db: AsyncSession, booking_id: UUID) -> bool:
    return await has_entry(db, booking_id, "refund_deposit", "damage_payout")


async def booking_total(db: AsyncSession, booking_id: UUID) -> Decimal:
    total = await db.scalar(
        select(func.coalesce(func.sum(LedgerEntry.amount), 0)).where(
            LedgerEntry.booking_id == booking_id
        )
    )
    return Decimal(total)
