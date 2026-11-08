"""Payment gateway contract.

The prototype only ships a database-backed mock implementation, but booking code depends
on this interface rather than on mock-specific behavior. A real marketplace provider can
therefore be added without teaching the booking state machine about provider APIs.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class PaymentResult:
    payment_id: UUID
    operation_id: UUID
    provider_reference: str
    status: str


class PaymentGatewayError(Exception):
    def __init__(self, code: str, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable

    def detail(self) -> dict[str, str | bool]:
        return {"code": self.code, "message": self.message, "retryable": self.retryable}


class PaymentGateway(Protocol):
    async def collect(
        self,
        db: AsyncSession,
        *,
        booking_id: UUID,
        amount: Decimal,
        payment_method: str,
        idempotency_key: str,
    ) -> PaymentResult: ...

    async def refund(
        self,
        db: AsyncSession,
        *,
        booking_id: UUID,
        amount: Decimal,
        idempotency_key: str,
    ) -> PaymentResult: ...

    async def payout(
        self,
        db: AsyncSession,
        *,
        booking_id: UUID,
        recipient_id: UUID,
        amount: Decimal,
        idempotency_key: str,
    ) -> PaymentResult: ...
