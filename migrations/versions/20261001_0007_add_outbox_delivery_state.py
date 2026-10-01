"""Add delivery state fields to the notification outbox.

Revision ID: 20261001_0007
Revises: 20260930_0006
Create Date: 2026-10-01
"""

from alembic import op
import sqlalchemy as sa


revision = "20261001_0007"
down_revision = "20260930_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "notification_outbox",
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("notification_outbox", sa.Column("last_error", sa.Text(), nullable=True))
    op.add_column(
        "notification_outbox",
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "notification_outbox",
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_notification_outbox_delivery_queue",
        "notification_outbox",
        ["status", "next_attempt_at", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_notification_outbox_delivery_queue", table_name="notification_outbox")
    op.drop_column("notification_outbox", "claimed_at")
    op.drop_column("notification_outbox", "next_attempt_at")
    op.drop_column("notification_outbox", "last_error")
    op.drop_column("notification_outbox", "attempt_count")
