"""Create the initial PassIt prototype schema.

Revision ID: 0001
Revises: None
"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")
    op.execute(
        "CREATE TYPE booking_state AS ENUM "
        "('requested','confirmed','handed_over','returned','settled','cancelled','disputed')"
    )
    op.execute(
        "CREATE TYPE ledger_type AS ENUM "
        "('hold_fee','hold_deposit','release_fee','refund_deposit','damage_payout')"
    )
    op.execute("CREATE TYPE media_stage AS ENUM ('listing','handover','return')")
    op.execute(
        """
        CREATE TABLE users (
          id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
          email CITEXT UNIQUE NOT NULL,
          password_hash TEXT NOT NULL,
          display_name TEXT NOT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE listings (
          id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
          owner_id UUID NOT NULL REFERENCES users(id),
          title TEXT NOT NULL,
          category TEXT NOT NULL,
          condition TEXT NOT NULL,
          price_day NUMERIC(10,2) NOT NULL CHECK (price_day > 0),
          price_week NUMERIC(10,2) CHECK (price_week > 0),
          price_month NUMERIC(10,2) CHECK (price_month > 0),
          deposit NUMERIC(10,2) NOT NULL CHECK (deposit >= 0),
          mrt_station TEXT,
          planning_area TEXT,
          latitude DOUBLE PRECISION,
          longitude DOUBLE PRECISION,
          status TEXT NOT NULL DEFAULT 'active',
          created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX listings_category_status_idx ON listings (category, status)")
    op.execute(
        "CREATE INDEX listings_search_idx ON listings "
        "USING gin (to_tsvector('english', title || ' ' || category))"
    )
    op.execute(
        """
        CREATE TABLE availability (
          id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
          listing_id UUID NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
          period DATERANGE NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE TABLE bookings (
          id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
          listing_id UUID NOT NULL REFERENCES listings(id),
          borrower_id UUID NOT NULL REFERENCES users(id),
          period DATERANGE NOT NULL,
          duration_type TEXT NOT NULL CHECK (duration_type IN ('day','week','month')),
          fee NUMERIC(10,2) NOT NULL CHECK (fee > 0),
          deposit NUMERIC(10,2) NOT NULL CHECK (deposit >= 0),
          state booking_state NOT NULL DEFAULT 'requested',
          handed_over_at TIMESTAMPTZ,
          returned_at TIMESTAMPTZ,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          CONSTRAINT no_overlap EXCLUDE USING gist (
            listing_id WITH =, period WITH &&
          ) WHERE (state IN ('confirmed','handed_over'))
        )
        """
    )
    op.execute(
        """
        CREATE TABLE ledger_entries (
          id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
          booking_id UUID NOT NULL REFERENCES bookings(id),
          account TEXT NOT NULL CHECK (account IN ('borrower','lender','platform_hold')),
          entry_type ledger_type NOT NULL,
          amount NUMERIC(10,2) NOT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX ledger_entries_booking_idx ON ledger_entries (booking_id)")
    op.execute(
        """
        CREATE TABLE media (
          id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
          listing_id UUID REFERENCES listings(id),
          booking_id UUID REFERENCES bookings(id),
          stage media_stage NOT NULL,
          s3_key TEXT NOT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE checklists (
          id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
          booking_id UUID NOT NULL REFERENCES bookings(id),
          stage media_stage NOT NULL,
          items JSONB NOT NULL,
          signed_by UUID REFERENCES users(id),
          signed_at TIMESTAMPTZ
        )
        """
    )
    op.execute(
        """
        CREATE TABLE reviews (
          id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
          booking_id UUID NOT NULL REFERENCES bookings(id),
          author_id UUID NOT NULL REFERENCES users(id),
          target_id UUID NOT NULL REFERENCES users(id),
          rating SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
          comment TEXT,
          UNIQUE (booking_id, author_id)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS reviews")
    op.execute("DROP TABLE IF EXISTS checklists")
    op.execute("DROP TABLE IF EXISTS media")
    op.execute("DROP TABLE IF EXISTS ledger_entries")
    op.execute("DROP TABLE IF EXISTS bookings")
    op.execute("DROP TABLE IF EXISTS availability")
    op.execute("DROP TABLE IF EXISTS listings")
    op.execute("DROP TABLE IF EXISTS users")
    op.execute("DROP TYPE IF EXISTS media_stage")
    op.execute("DROP TYPE IF EXISTS ledger_type")
    op.execute("DROP TYPE IF EXISTS booking_state")
