"""Mark deleted (anonymised) accounts.

Revision ID: 0004
Revises: 0003
"""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Set when a person deletes their account. The row stays, scrubbed of personal data, because
    # other people's bookings, ledger entries and reviews still point at it.
    op.execute("ALTER TABLE users ADD COLUMN deleted_at TIMESTAMPTZ")


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN deleted_at")
