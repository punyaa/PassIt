"""Read-only payment audit API for booking participants."""

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.auth.dependencies import CurrentUser
from app.core.db import DbSession
from app.models import Booking, Listing, Payment, PaymentOperation
from app.schemas import ApiModel

router = APIRouter(prefix="/payments", tags=["payments"])


class PaymentOperationResponse(ApiModel):
    id: UUID
    operation: Literal["charge", "refund", "payout"]
    amount: Decimal
    status: Literal["succeeded", "failed"]
    recipient_id: UUID | None
    provider_reference: str
    failure_code: str | None
    created_at: datetime


class BookingPaymentResponse(ApiModel):
    id: UUID
    booking_id: UUID
    amount: Decimal
    currency: Literal["SGD"]
    status: Literal["captured", "partially_refunded", "refunded", "failed", "cancelled"]
    provider: Literal["mock"]
    provider_reference: str
    payment_method_label: str
    failure_code: str | None
    created_at: datetime
    updated_at: datetime
    operations: list[PaymentOperationResponse]


@router.get(
    "/bookings/{booking_id}",
    response_model=BookingPaymentResponse,
    operation_id="getBookingPayment",
)
async def get_booking_payment(
    booking_id: UUID, user: CurrentUser, db: DbSession
) -> BookingPaymentResponse:
    booking = await db.get(Booking, booking_id)
    listing = booking and await db.get(Listing, booking.listing_id)
    if booking is None or listing is None or user.id not in (booking.borrower_id, listing.owner_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Payment not found")

    payment = await db.scalar(select(Payment).where(Payment.booking_id == booking_id))
    if payment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Payment not found")
    operations = list(
        await db.scalars(
            select(PaymentOperation)
            .where(PaymentOperation.payment_id == payment.id)
            .order_by(PaymentOperation.created_at, PaymentOperation.id)
        )
    )
    return BookingPaymentResponse(
        id=payment.id,
        booking_id=payment.booking_id,
        amount=payment.amount,
        currency=payment.currency,
        status=payment.status,
        provider=payment.provider,
        provider_reference=payment.provider_reference,
        payment_method_label=payment.payment_method_label,
        failure_code=payment.failure_code,
        created_at=payment.created_at,
        updated_at=payment.updated_at,
        operations=[
            PaymentOperationResponse(
                id=operation.id,
                operation=operation.operation,
                amount=operation.amount,
                status=operation.status,
                recipient_id=operation.recipient_id,
                provider_reference=operation.provider_reference,
                failure_code=operation.failure_code,
                created_at=operation.created_at,
            )
            for operation in operations
        ],
    )
