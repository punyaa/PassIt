"""Meetups belong to a booking: one to hand the item over, one to return it.

Revision ID: 0008
Revises: 0007
"""

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Nullable: meetups proposed before this change have no booking and stay as history.
    op.execute(
        "ALTER TABLE meetups ADD COLUMN booking_id UUID REFERENCES bookings(id) ON DELETE CASCADE"
    )
    op.execute(
        "ALTER TABLE meetups ADD COLUMN purpose TEXT CHECK (purpose IN ('handover', 'return'))"
    )
    # A meetup is completed once the handover or return it was arranged for is recorded.
    op.execute("ALTER TYPE meetup_status ADD VALUE IF NOT EXISTS 'completed'")
    op.execute("ALTER TABLE meetup_events DROP CONSTRAINT meetup_events_kind_check")
    op.execute(
        "ALTER TABLE meetup_events ADD CONSTRAINT meetup_events_kind_check "
        "CHECK (kind IN ('propose', 'counter', 'accept', 'decline', 'cancel', 'complete'))"
    )
    # One proposed or scheduled meetup per booking and purpose (replaces one-open-per-borrower-
    # and-listing, which would stop a borrower arranging two bookings of the same item).
    op.execute("DROP INDEX meetups_one_open_per_borrower")
    op.execute(
        "CREATE UNIQUE INDEX meetups_one_live_per_booking ON meetups (booking_id, purpose) "
        "WHERE status IN ('pending', 'accepted')"
    )


def downgrade() -> None:
    op.execute("DROP INDEX meetups_one_live_per_booking")
    op.execute(
        "CREATE UNIQUE INDEX meetups_one_open_per_borrower "
        "ON meetups (listing_id, borrower_id) WHERE status = 'pending'"
    )
    op.execute("DELETE FROM meetup_events WHERE kind = 'complete'")
    op.execute("ALTER TABLE meetup_events DROP CONSTRAINT meetup_events_kind_check")
    op.execute(
        "ALTER TABLE meetup_events ADD CONSTRAINT meetup_events_kind_check "
        "CHECK (kind IN ('propose', 'counter', 'accept', 'decline', 'cancel'))"
    )
    # Postgres cannot drop an enum value; completed meetups fall back to cancelled.
    op.execute("UPDATE meetups SET status = 'cancelled' WHERE status = 'completed'")
    op.execute("ALTER TABLE meetups DROP COLUMN purpose")
    op.execute("ALTER TABLE meetups DROP COLUMN booking_id")
