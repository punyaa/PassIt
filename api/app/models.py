"""ORM mapping of the Alembic-owned schema.

Alembic migrations are the source of truth for the database; these classes only mirror
the tables so the domain modules can query them. Change a migration first, then this file.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, SmallInteger, Text, text
from sqlalchemy.dialects.postgresql import DATERANGE, ENUM, JSONB, Range
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

booking_state = ENUM(
    "requested",
    "confirmed",
    "handed_over",
    "returned",
    "settled",
    "cancelled",
    "disputed",
    name="booking_state",
    create_type=False,
)
ledger_type = ENUM(
    "hold_fee",
    "hold_deposit",
    "release_fee",
    "refund_deposit",
    "damage_payout",
    name="ledger_type",
    create_type=False,
)
media_stage = ENUM("listing", "handover", "return", name="media_stage", create_type=False)

Money = Numeric(10, 2)
UUID_DEFAULT = text("uuid_generate_v4()")
NOW = text("now()")


class Base(DeclarativeBase):
    type_annotation_map = {datetime: DateTime(timezone=True)}


# --- Platform ----------------------------------------------------------------


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=UUID_DEFAULT)
    email: Mapped[str] = mapped_column(Text)
    password_hash: Mapped[str] = mapped_column(Text)
    display_name: Mapped[str] = mapped_column(Text)
    bio: Mapped[str | None] = mapped_column(Text)
    avatar_key: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=NOW)


# --- B3 Catalogue ------------------------------------------------------------


class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=UUID_DEFAULT)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str] = mapped_column(Text)
    condition: Mapped[str] = mapped_column(Text)
    price_day: Mapped[Decimal] = mapped_column(Money)
    price_week: Mapped[Decimal | None] = mapped_column(Money)
    price_month: Mapped[Decimal | None] = mapped_column(Money)
    deposit: Mapped[Decimal] = mapped_column(Money)
    mrt_station: Mapped[str | None] = mapped_column(Text)
    planning_area: Mapped[str | None] = mapped_column(Text)
    latitude: Mapped[float | None]
    longitude: Mapped[float | None]
    status: Mapped[str] = mapped_column(Text, server_default=text("'active'"))
    created_at: Mapped[datetime] = mapped_column(server_default=NOW)


class Media(Base):
    __tablename__ = "media"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=UUID_DEFAULT)
    listing_id: Mapped[UUID | None] = mapped_column(ForeignKey("listings.id"))
    booking_id: Mapped[UUID | None] = mapped_column(ForeignKey("bookings.id"))
    uploaded_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    stage: Mapped[str] = mapped_column(media_stage)
    s3_key: Mapped[str] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(server_default=NOW)


# --- B1 Booking --------------------------------------------------------------


class Availability(Base):
    __tablename__ = "availability"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=UUID_DEFAULT)
    listing_id: Mapped[UUID] = mapped_column(ForeignKey("listings.id"))
    period: Mapped[Range[date]] = mapped_column(DATERANGE)


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=UUID_DEFAULT)
    listing_id: Mapped[UUID] = mapped_column(ForeignKey("listings.id"))
    borrower_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    period: Mapped[Range[date]] = mapped_column(DATERANGE)
    duration_type: Mapped[str] = mapped_column(Text)
    fee: Mapped[Decimal] = mapped_column(Money)
    deposit: Mapped[Decimal] = mapped_column(Money)
    state: Mapped[str] = mapped_column(booking_state, server_default=text("'requested'"))
    handed_over_at: Mapped[datetime | None]
    returned_at: Mapped[datetime | None]
    fee_release_at: Mapped[datetime | None]
    settled_at: Mapped[datetime | None]
    cancelled_at: Mapped[datetime | None]
    damage_severity: Mapped[str | None] = mapped_column(Text)
    damage_notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=NOW)

    @property
    def start_date(self) -> date:
        return range_bounds(self.period)[0]

    @property
    def end_date(self) -> date:
        return range_bounds(self.period)[1]


class Checklist(Base):
    __tablename__ = "checklists"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=UUID_DEFAULT)
    booking_id: Mapped[UUID] = mapped_column(ForeignKey("bookings.id"))
    stage: Mapped[str] = mapped_column(media_stage)
    items: Mapped[list[dict]] = mapped_column(JSONB)
    signed_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    signed_at: Mapped[datetime | None]


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=UUID_DEFAULT)
    booking_id: Mapped[UUID] = mapped_column(ForeignKey("bookings.id"))
    author_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    target_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    rating: Mapped[int] = mapped_column(SmallInteger)
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=NOW)


# --- B2 Transactions ---------------------------------------------------------


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=UUID_DEFAULT)
    booking_id: Mapped[UUID] = mapped_column(ForeignKey("bookings.id"))
    account: Mapped[str] = mapped_column(Text)
    entry_type: Mapped[str] = mapped_column(ledger_type)
    amount: Mapped[Decimal] = mapped_column(Money)
    created_at: Mapped[datetime] = mapped_column(server_default=NOW)


class SavedListing(Base):
    __tablename__ = "saved_listings"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    listing_id: Mapped[UUID] = mapped_column(ForeignKey("listings.id"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(server_default=NOW)


# --- Date ranges -------------------------------------------------------------


def inclusive_range(start: date, end: date) -> Range[date]:
    """The API speaks inclusive [start, end]; Postgres stores daterange as [start, end+1)."""
    return Range(start, end, bounds="[]")


def range_bounds(period: Range[date]) -> tuple[date, date]:
    """Convert a stored daterange back to inclusive start and end dates."""
    start = period.lower if period.lower_inc else period.lower + timedelta(days=1)
    end = period.upper if period.upper_inc else period.upper - timedelta(days=1)
    return start, end
