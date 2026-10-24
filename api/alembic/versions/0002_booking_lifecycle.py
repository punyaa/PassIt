"""Add booking lifecycle, listing description and evidence integrity columns.

Revision ID: 0002
Revises: 0001
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE listings ADD COLUMN description TEXT")
    op.execute(
        "ALTER TABLE listings ADD CONSTRAINT listings_status_check "
        "CHECK (status IN ('active','paused','archived'))"
    )
    op.execute("CREATE INDEX listings_owner_idx ON listings (owner_id)")

    op.execute("ALTER TABLE bookings ADD COLUMN fee_release_at TIMESTAMPTZ")
    op.execute("ALTER TABLE bookings ADD COLUMN settled_at TIMESTAMPTZ")
    op.execute("ALTER TABLE bookings ADD COLUMN cancelled_at TIMESTAMPTZ")
    op.execute(
        "ALTER TABLE bookings ADD COLUMN damage_severity TEXT "
        "CHECK (damage_severity IN ('none','minor','moderate','severe','total'))"
    )
    op.execute("ALTER TABLE bookings ADD COLUMN damage_notes TEXT")
    op.execute("CREATE INDEX bookings_borrower_idx ON bookings (borrower_id)")
    op.execute("CREATE INDEX bookings_listing_idx ON bookings (listing_id)")
    op.execute(
        "CREATE INDEX bookings_release_due_idx ON bookings (fee_release_at) "
        "WHERE fee_release_at IS NOT NULL"
    )

    op.execute("CREATE INDEX availability_listing_idx ON availability (listing_id)")

    # Condition evidence is written once and never deleted or reused.
    op.execute("ALTER TABLE media ADD COLUMN uploaded_by UUID REFERENCES users(id)")
    op.execute("ALTER TABLE media ADD CONSTRAINT media_s3_key_unique UNIQUE (s3_key)")
    op.execute("CREATE INDEX media_listing_idx ON media (listing_id)")
    op.execute("CREATE INDEX media_booking_idx ON media (booking_id)")

    op.execute(
        "ALTER TABLE checklists ADD CONSTRAINT checklists_booking_stage_unique "
        "UNIQUE (booking_id, stage)"
    )

    op.execute("ALTER TABLE reviews ADD COLUMN created_at TIMESTAMPTZ NOT NULL DEFAULT now()")
    op.execute("CREATE INDEX reviews_target_idx ON reviews (target_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS reviews_target_idx")
    op.execute("ALTER TABLE reviews DROP COLUMN IF EXISTS created_at")
    op.execute("ALTER TABLE checklists DROP CONSTRAINT IF EXISTS checklists_booking_stage_unique")
    op.execute("DROP INDEX IF EXISTS media_booking_idx")
    op.execute("DROP INDEX IF EXISTS media_listing_idx")
    op.execute("ALTER TABLE media DROP CONSTRAINT IF EXISTS media_s3_key_unique")
    op.execute("ALTER TABLE media DROP COLUMN IF EXISTS uploaded_by")
    op.execute("DROP INDEX IF EXISTS availability_listing_idx")
    op.execute("DROP INDEX IF EXISTS bookings_release_due_idx")
    op.execute("DROP INDEX IF EXISTS bookings_listing_idx")
    op.execute("DROP INDEX IF EXISTS bookings_borrower_idx")
    for column in (
        "damage_notes",
        "damage_severity",
        "cancelled_at",
        "settled_at",
        "fee_release_at",
    ):
        op.execute(f"ALTER TABLE bookings DROP COLUMN IF EXISTS {column}")
    op.execute("DROP INDEX IF EXISTS listings_owner_idx")
    op.execute("ALTER TABLE listings DROP CONSTRAINT IF EXISTS listings_status_check")
    op.execute("ALTER TABLE listings DROP COLUMN IF EXISTS description")
