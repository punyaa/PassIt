"""Add persisted mock payment and operation records.

Revision ID: 0003
Revises: 0002
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE payments (
          id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
          booking_id UUID NOT NULL UNIQUE REFERENCES bookings(id) ON DELETE CASCADE,
          amount NUMERIC(10,2) NOT NULL CHECK (amount > 0),
          currency TEXT NOT NULL DEFAULT 'SGD' CHECK (currency = 'SGD'),
          status TEXT NOT NULL CHECK (
            status IN ('captured','partially_refunded','refunded','failed','cancelled')
          ),
          provider TEXT NOT NULL DEFAULT 'mock' CHECK (provider = 'mock'),
          provider_reference TEXT NOT NULL UNIQUE,
          payment_method_label TEXT NOT NULL,
          failure_code TEXT,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE payment_operations (
          id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
          payment_id UUID NOT NULL REFERENCES payments(id) ON DELETE CASCADE,
          operation TEXT NOT NULL CHECK (operation IN ('charge','refund','payout')),
          amount NUMERIC(10,2) NOT NULL CHECK (amount > 0),
          status TEXT NOT NULL CHECK (status IN ('succeeded','failed')),
          recipient_id UUID REFERENCES users(id),
          idempotency_key TEXT NOT NULL UNIQUE,
          provider_reference TEXT NOT NULL UNIQUE,
          failure_code TEXT,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX payment_operations_payment_idx ON payment_operations (payment_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS payment_operations")
    op.execute("DROP TABLE IF EXISTS payments")
