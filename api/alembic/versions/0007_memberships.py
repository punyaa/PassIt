"""Add PassIt Plus memberships and their audit history.

Revision ID: 0007
Revises: 0006
"""

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE memberships (
          id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
          user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
          plan TEXT NOT NULL CHECK (plan IN ('saver','eco-saver','mega-saver')),
          status TEXT NOT NULL CHECK (status IN ('active','expired','cancelled')),
          current_period_start TIMESTAMPTZ NOT NULL DEFAULT now(),
          current_period_end TIMESTAMPTZ,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE membership_events (
          id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
          membership_id UUID NOT NULL REFERENCES memberships(id) ON DELETE CASCADE,
          event TEXT NOT NULL CHECK (
            event IN ('created','upgraded','downgraded','renewed','expired','cancelled')
          ),
          from_plan TEXT CHECK (from_plan IN ('saver','eco-saver','mega-saver')),
          to_plan TEXT CHECK (to_plan IN ('saver','eco-saver','mega-saver')),
          created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX membership_events_membership_idx ON membership_events (membership_id)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS membership_events")
    op.execute("DROP TABLE IF EXISTS memberships")
