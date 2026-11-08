"""Meetup proposals: a borrower and a lender agree on a time, place and price.

Revision ID: 0005
Revises: 0004
"""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE TYPE meetup_status AS ENUM ('pending', 'accepted', 'declined', 'cancelled')")
    # The row holds the terms currently on the table. `proposed_by` made the latest offer, so
    # the other party is the one who may accept, counter or decline it.
    op.execute("""
        CREATE TABLE meetups (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            listing_id UUID NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
            borrower_id UUID NOT NULL REFERENCES users(id),
            lender_id UUID NOT NULL REFERENCES users(id),
            status meetup_status NOT NULL DEFAULT 'pending',
            meet_at TIMESTAMPTZ NOT NULL,
            location TEXT NOT NULL CHECK (length(location) BETWEEN 1 AND 200),
            price NUMERIC(10, 2) NOT NULL CHECK (price >= 0),
            proposed_by UUID NOT NULL REFERENCES users(id),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CHECK (borrower_id <> lender_id),
            CHECK (proposed_by IN (borrower_id, lender_id))
        )
    """)
    # One open negotiation per borrower and listing; a new one can start once it is closed.
    op.execute(
        "CREATE UNIQUE INDEX meetups_one_open_per_borrower "
        "ON meetups (listing_id, borrower_id) WHERE status = 'pending'"
    )
    op.execute("CREATE INDEX meetups_lender_idx ON meetups (lender_id, status)")
    op.execute("CREATE INDEX meetups_borrower_idx ON meetups (borrower_id, status)")
    # The conversation: every proposal, counter-offer and response, with an optional message.
    op.execute("""
        CREATE TABLE meetup_events (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            meetup_id UUID NOT NULL REFERENCES meetups(id) ON DELETE CASCADE,
            author_id UUID NOT NULL REFERENCES users(id),
            kind TEXT NOT NULL
                CHECK (kind IN ('propose', 'counter', 'accept', 'decline', 'cancel')),
            meet_at TIMESTAMPTZ,
            location TEXT,
            price NUMERIC(10, 2),
            message TEXT CHECK (length(message) <= 500),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX meetup_events_meetup_idx ON meetup_events (meetup_id, created_at)")


def downgrade() -> None:
    op.execute("DROP TABLE meetup_events")
    op.execute("DROP TABLE meetups")
    op.execute("DROP TYPE meetup_status")
