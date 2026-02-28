"""Add anomaly_detection_configs and detected_anomalies tables

Revision ID: c5d6e7f8a9b0
Revises: b3c4d5e6f7a8
Create Date: 2026-03-02

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c5d6e7f8a9b0'
down_revision = 'b3c4d5e6f7a8'
branch_labels = None
depends_on = None


def upgrade():
    # ------------------------------------------------------------------
    # anomaly_detection_configs
    # Per-account sensitivity settings for the anomaly detector.
    # ------------------------------------------------------------------
    op.create_table(
        'anomaly_detection_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        # Z-score sigma threshold: 1.5 | 2.0 | 2.5
        sa.Column('sensitivity', sa.Float(), nullable=False, server_default=sa.text('2.0')),
        # Rolling window in days used to compute the baseline
        sa.Column('baseline_days', sa.Integer(), nullable=False, server_default=sa.text('30')),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('account_id', name='uq_anomaly_detection_configs_account'),
    )
    with op.batch_alter_table('anomaly_detection_configs', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_anomaly_detection_configs_account_id'),
            ['account_id'],
            unique=False,
        )

    # ------------------------------------------------------------------
    # detected_anomalies
    # Individual anomaly events: one row per account per day.
    # ------------------------------------------------------------------
    op.create_table(
        'detected_anomalies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        # Calendar date of the anomalous day
        sa.Column('anomaly_date', sa.Date(), nullable=False),
        # Cost on the anomalous day
        sa.Column('daily_cost', sa.Numeric(10, 4), nullable=False, server_default=sa.text('0')),
        # Statistical baseline
        sa.Column('baseline_mean', sa.Numeric(10, 4), nullable=False, server_default=sa.text('0')),
        sa.Column('baseline_std', sa.Numeric(10, 4), nullable=False, server_default=sa.text('0')),
        # Z-score: signed deviation in standard deviations
        sa.Column('z_score', sa.Float(), nullable=False, server_default=sa.text('0')),
        # Dollar difference vs baseline mean (positive = over baseline)
        sa.Column('cost_delta', sa.Numeric(10, 4), nullable=False, server_default=sa.text('0')),
        # low | medium | high | critical
        sa.Column('severity', sa.String(length=20), nullable=False, server_default=sa.text("'low'")),
        sa.Column('is_acknowledged', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('detected_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        # One anomaly record per account per day
        sa.UniqueConstraint(
            'account_id', 'anomaly_date', name='uq_detected_anomaly_account_date'
        ),
    )
    with op.batch_alter_table('detected_anomalies', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_detected_anomalies_account_id'),
            ['account_id'],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f('ix_detected_anomalies_anomaly_date'),
            ['anomaly_date'],
            unique=False,
        )
        # Efficient lookups for the dashboard: unacknowledged alerts by account
        batch_op.create_index(
            'ix_detected_anomalies_account_acknowledged',
            ['account_id', 'is_acknowledged'],
            unique=False,
        )


def downgrade():
    with op.batch_alter_table('detected_anomalies', schema=None) as batch_op:
        batch_op.drop_index('ix_detected_anomalies_account_acknowledged')
        batch_op.drop_index(batch_op.f('ix_detected_anomalies_anomaly_date'))
        batch_op.drop_index(batch_op.f('ix_detected_anomalies_account_id'))

    op.drop_table('detected_anomalies')

    with op.batch_alter_table('anomaly_detection_configs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_anomaly_detection_configs_account_id'))

    op.drop_table('anomaly_detection_configs')
