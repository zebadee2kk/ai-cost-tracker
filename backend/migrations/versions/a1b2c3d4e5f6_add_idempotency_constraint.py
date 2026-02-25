"""Add unique constraint for idempotent usage ingestion

Adds:
- Unique constraint on (account_id, service_id, timestamp, request_type)
- source column to distinguish api vs. manual entries
- updated_at column for tracking upsert timestamps

Revision ID: a1b2c3d4e5f6
Revises: 8f80d9282c6b
Create Date: 2026-02-25
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '8f80d9282c6b'
branch_labels = None
depends_on = None


def upgrade():
    # Add source field to distinguish api-fetched vs. manual entries
    op.add_column(
        'usage_records',
        sa.Column('source', sa.String(50), nullable=False, server_default='api')
    )

    # Add updated_at for tracking upsert timestamps
    op.add_column(
        'usage_records',
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True)
    )

    # Add unique constraint to prevent duplicate records during repeated syncs.
    # timestamp is always stored as midnight UTC for daily records, so this
    # uniquely identifies one daily record per account/service/request_type.
    op.create_unique_constraint(
        'uq_usage_record_idempotency',
        'usage_records',
        ['account_id', 'service_id', 'timestamp', 'request_type']
    )


def downgrade():
    op.drop_constraint('uq_usage_record_idempotency', 'usage_records', type_='unique')
    op.drop_column('usage_records', 'updated_at')
    op.drop_column('usage_records', 'source')
