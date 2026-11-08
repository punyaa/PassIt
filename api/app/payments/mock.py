"""Deterministic, database-backed mock marketplace payment gateway."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Payment, PaymentOperation
from app.payments.gateway import PaymentGatewayError, PaymentResult

MOCK_FAILURES: dict[str, tuple[str, str, bool]] = {
    "pm_mock_declined": ("card_declined", "The mock payment was declined.", False),
    "pm_mock_insufficient_funds": (
        "insufficient_funds",
        "The mock payment method has insufficient funds.",
        False,
    ),
    "pm_mock_expired": ("expired_payment_method", "The mock payment method has expired.", False),
    "pm_mock_processing_error": (
        "processing_error",
        "The mock gateway had a temporary processing error. Please retry.",
        True,
    ),
}
MOCK_SUCCESS = "pm_mock_success"


def _reference(prefix: str) -> str:
    return f"mock_{prefix}_{uuid4().hex}"


class MockPaymentGateway:
    """Persists successful operations in the caller's database transaction.

    This deliberately avoids sleeps and random failures: a test token always produces the
    same outcome. Because records use the caller's session, a failed booking or ledger write
    also rolls back the mock charge.
    """

    async def _existing(
        self, db: AsyncSession, idempotency_key: str
    ) -> PaymentResult | None:
        operation = await db.scalar(
            select(PaymentOperation).where(
                PaymentOperation.idempotency_key == idempotency_key
            )
        )
        if operation is None:
            return None
        return PaymentResult(
            payment_id=operation.payment_id,
            operation_id=operation.id,
            provider_reference=operation.provider_reference,
            status=operation.status,
        )

    async def _payment(self, db: AsyncSession, booking_id: UUID) -> Payment:
        payment = await db.scalar(
            select(Payment).where(Payment.booking_id == booking_id).with_for_update()
        )
        if payment is None:
            raise PaymentGatewayError(
                "payment_not_found", "No captured mock payment exists for this booking."
            )
        return payment

    async def _distributed(self, db: AsyncSession, payment_id: UUID) -> Decimal:
        return Decimal(
            await db.scalar(
                select(func.coalesce(func.sum(PaymentOperation.amount), 0)).where(
                    PaymentOperation.payment_id == payment_id,
                    PaymentOperation.operation.in_(("refund", "payout")),
                    PaymentOperation.status == "succeeded",
                )
            )
        )

    async def collect(
        self,
        db: AsyncSession,
        *,
        booking_id: UUID,
        amount: Decimal,
        payment_method: str,
        idempotency_key: str,
    ) -> PaymentResult:
        if existing := await self._existing(db, idempotency_key):
            return existing
        if payment_method in MOCK_FAILURES:
            code, message, retryable = MOCK_FAILURES[payment_method]
            raise PaymentGatewayError(code, message, retryable=retryable)
        if payment_method != MOCK_SUCCESS:
            raise PaymentGatewayError(
                "invalid_payment_method", "Unknown mock payment method."
            )

        payment_id, operation_id = uuid4(), uuid4()
        payment_reference = _reference("pay")
        operation_reference = _reference("charge")
        db.add(
            Payment(
                id=payment_id,
                booking_id=booking_id,
                amount=amount,
                currency="SGD",
                status="captured",
                provider="mock",
                provider_reference=payment_reference,
                payment_method_label="Mock Visa ending 4242",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )
        db.add(
            PaymentOperation(
                id=operation_id,
                payment_id=payment_id,
                operation="charge",
                amount=amount,
                status="succeeded",
                idempotency_key=idempotency_key,
                provider_reference=operation_reference,
                created_at=datetime.now(UTC),
            )
        )
        await db.flush()
        return PaymentResult(payment_id, operation_id, operation_reference, "succeeded")

    async def refund(
        self,
        db: AsyncSession,
        *,
        booking_id: UUID,
        amount: Decimal,
        idempotency_key: str,
    ) -> PaymentResult:
        if existing := await self._existing(db, idempotency_key):
            return existing
        payment = await self._payment(db, booking_id)
        distributed = await self._distributed(db, payment.id)
        refunded = Decimal(
            await db.scalar(
                select(func.coalesce(func.sum(PaymentOperation.amount), 0)).where(
                    PaymentOperation.payment_id == payment.id,
                    PaymentOperation.operation == "refund",
                    PaymentOperation.status == "succeeded",
                )
            )
        )
        if amount <= 0 or distributed + amount > payment.amount:
            raise PaymentGatewayError(
                "invalid_refund", "Mock refund exceeds the undistributed captured amount."
            )

        operation_id = uuid4()
        operation_reference = _reference("refund")
        db.add(
            PaymentOperation(
                id=operation_id,
                payment_id=payment.id,
                operation="refund",
                amount=amount,
                status="succeeded",
                idempotency_key=idempotency_key,
                provider_reference=operation_reference,
                created_at=datetime.now(UTC),
            )
        )
        payment.status = "refunded" if refunded + amount == payment.amount else "partially_refunded"
        payment.updated_at = datetime.now(UTC)
        await db.flush()
        return PaymentResult(payment.id, operation_id, operation_reference, "succeeded")

    async def payout(
        self,
        db: AsyncSession,
        *,
        booking_id: UUID,
        recipient_id: UUID,
        amount: Decimal,
        idempotency_key: str,
    ) -> PaymentResult:
        if existing := await self._existing(db, idempotency_key):
            return existing
        payment = await self._payment(db, booking_id)
        distributed = await self._distributed(db, payment.id)
        if amount <= 0 or distributed + amount > payment.amount:
            raise PaymentGatewayError(
                "invalid_payout", "Mock payout exceeds the undistributed captured amount."
            )

        operation_id = uuid4()
        operation_reference = _reference("payout")
        db.add(
            PaymentOperation(
                id=operation_id,
                payment_id=payment.id,
                operation="payout",
                amount=amount,
                status="succeeded",
                recipient_id=recipient_id,
                idempotency_key=idempotency_key,
                provider_reference=operation_reference,
                created_at=datetime.now(UTC),
            )
        )
        payment.updated_at = datetime.now(UTC)
        await db.flush()
        return PaymentResult(payment.id, operation_id, operation_reference, "succeeded")
