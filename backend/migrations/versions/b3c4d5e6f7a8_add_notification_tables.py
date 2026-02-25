"""Add notification_preferences, notification_queue, and notification_history tables

Revision ID: b3c4d5e6f7a8
Revises: a1b2c3d4e5f6
Create Date: 2026-02-25

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b3c4d5e6f7a8'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    # ------------------------------------------------------------------
    # notification_preferences
    # Stores per-user, per-channel notification settings.
    # ------------------------------------------------------------------
    op.create_table(
        'notification_preferences',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('channel', sa.String(length=50), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        # config holds channel-specific data (webhook URL, email address, etc.)
        sa.Column('config', sa.JSON(), nullable=True),
        # alert_types is a JSON list: ['budget', 'anomaly', 'system']
        sa.Column('alert_types', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'channel', name='uq_notification_preferences_user_channel'),
    )
    with op.batch_alter_table('notification_preferences', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_notification_preferences_user_id'),
            ['user_id'],
            unique=False,
        )

    # ------------------------------------------------------------------
    # notification_queue
    # Outbound notification jobs; consumed by the dispatcher service.
    # ------------------------------------------------------------------
    op.create_table(
        'notification_queue',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('alert_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('channel', sa.String(length=50), nullable=False),
        sa.Column('recipient', sa.Text(), nullable=False),
        # priority: 1=low, 2=medium, 3=high
        sa.Column('priority', sa.Integer(), nullable=False, server_default=sa.text('1')),
        # status: 'pending', 'sent', 'failed', 'cancelled'
        sa.Column('status', sa.String(length=20), nullable=False, server_default=sa.text("'pending'")),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('max_retries', sa.Integer(), nullable=False, server_default=sa.text('3')),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['alert_id'], ['alerts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('notification_queue', schema=None) as batch_op:
        # Dispatcher queries by status + priority for efficient pickup.
        batch_op.create_index(
            'ix_notification_queue_status_priority',
            ['status', 'priority'],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f('ix_notification_queue_user_id'),
            ['user_id'],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f('ix_notification_queue_alert_id'),
            ['alert_id'],
            unique=False,
        )

    # ------------------------------------------------------------------
    # notification_history
    # Immutable audit log used for rate-limiting and delivery analytics.
    # ------------------------------------------------------------------
    op.create_table(
        'notification_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('notification_id', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('channel', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        # duration_ms: time taken to deliver the notification
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ['notification_id'], ['notification_queue.id'], ondelete='SET NULL'
        ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('notification_history', schema=None) as batch_op:
        # Rate limiter queries history by user + channel + created_at.
        batch_op.create_index(
            'ix_notification_history_created_at',
            ['created_at'],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f('ix_notification_history_user_id'),
            ['user_id'],
            unique=False,
        )
        batch_op.create_index(
            'ix_notification_history_user_channel',
            ['user_id', 'channel'],
            unique=False,
        )


def downgrade():
    with op.batch_alter_table('notification_history', schema=None) as batch_op:
        batch_op.drop_index('ix_notification_history_user_channel')
        batch_op.drop_index(batch_op.f('ix_notification_history_user_id'))
        batch_op.drop_index('ix_notification_history_created_at')

    op.drop_table('notification_history')

    with op.batch_alter_table('notification_queue', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_notification_queue_alert_id'))
        batch_op.drop_index(batch_op.f('ix_notification_queue_user_id'))
        batch_op.drop_index('ix_notification_queue_status_priority')

    op.drop_table('notification_queue')

    with op.batch_alter_table('notification_preferences', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_notification_preferences_user_id'))

    op.drop_table('notification_preferences')
