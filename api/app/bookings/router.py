from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from fastapi import APIRouter

from app.core.stubs import not_implemented
from app.schemas import ApiModel

router = APIRouter(prefix="/bookings", tags=["bookings"])

BookingState = Literal[
    "requested", "confirmed", "handed_over", "returned", "settled", "cancelled", "disputed"
]


class BookingCreate(ApiModel):
    listing_id: UUID
    start_date: date
    end_date: date
    duration_type: Literal["day", "week", "month"]


class Booking(ApiModel):
    id: UUID
    listing_id: UUID
    borrower_id: UUID
    start_date: date
    end_date: date
    duration_type: Literal["day", "week", "month"]
    fee: Decimal
    deposit: Decimal
    state: BookingState


class ChecklistItem(ApiModel):
    label: str
    checked: bool


class ChecklistSubmission(ApiModel):
    items: list[ChecklistItem]
    media_keys: list[str]


class DamageSubmission(ApiModel):
    severity: Literal["minor", "moderate", "severe", "total"]
    notes: str


@router.post("", response_model=Booking, operation_id="createBooking")
async def create_booking(_: BookingCreate) -> Booking:
    not_implemented("transactional conflict-safe booking", "B1 Booking")


@router.post("/{booking_id}/handover", response_model=Booking, operation_id="handoverBooking")
async def handover_booking(booking_id: UUID, _: ChecklistSubmission) -> Booking:
    not_implemented(f"handover for {booking_id}", "B1 Booking")


@router.post("/{booking_id}/return", response_model=Booking, operation_id="returnBooking")
async def return_booking(booking_id: UUID, _: ChecklistSubmission) -> Booking:
    not_implemented(f"return for {booking_id}", "B1 Booking")


@router.post("/{booking_id}/damage", response_model=Booking, operation_id="reportBookingDamage")
async def report_booking_damage(booking_id: UUID, _: DamageSubmission) -> Booking:
    not_implemented(f"damage settlement for {booking_id}", "B1 Booking and B2 Transactions")
