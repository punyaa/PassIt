"""Prototype profiles, saved listings and listing photo order.

Revision ID: 0003
Revises: 0002
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN bio TEXT CHECK (length(bio) <= 500)")
    op.execute("ALTER TABLE users ADD COLUMN avatar_key TEXT")
    op.execute("ALTER TABLE media ADD COLUMN position INTEGER NOT NULL DEFAULT 0")
    op.execute("""
        WITH ordered AS (
            SELECT id, row_number() OVER (
                PARTITION BY listing_id ORDER BY created_at, id
            ) - 1 AS position FROM media WHERE stage = 'listing'
        ) UPDATE media SET position = ordered.position FROM ordered WHERE media.id = ordered.id
    """)
    op.execute("""
        CREATE TABLE saved_listings (
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            listing_id UUID NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (user_id, listing_id)
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE saved_listings")
    op.execute("ALTER TABLE media DROP COLUMN position")
    op.execute("ALTER TABLE users DROP COLUMN avatar_key")
    op.execute("ALTER TABLE users DROP COLUMN bio")
