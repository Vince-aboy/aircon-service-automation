"""Add audited local-staff review decisions for booking requests.

Revision ID: 20260930_0004
Revises: 20260930_0003
Create Date: 2026-09-30
"""

from alembic import op
import sqlalchemy as sa


revision = "20260930_0004"
down_revision = "20260930_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_booking_requests_status", "booking_requests", type_="check")
    op.create_check_constraint(
        "ck_booking_requests_status",
        "booking_requests",
        "status IN ('pending_review', 'approved_for_scheduling', 'cancelled')",
    )
    op.create_table(
        "booking_request_status_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("booking_request_id", sa.Integer(), sa.ForeignKey("booking_requests.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("from_status", sa.String(length=32), nullable=False),
        sa.Column("to_status", sa.String(length=32), nullable=False),
        sa.Column("actor_type", sa.String(length=32), nullable=False, server_default="local_staff"),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("note", sa.Text(), nullable=True),
        sa.CheckConstraint("actor_type = 'local_staff'", name="ck_booking_request_history_local_staff"),
    )


def downgrade() -> None:
    op.execute("UPDATE booking_requests SET status = 'pending_review' WHERE status = 'approved_for_scheduling'")
    op.drop_table("booking_request_status_history")
    op.drop_constraint("ck_booking_requests_status", "booking_requests", type_="check")
    op.create_check_constraint(
        "ck_booking_requests_status",
        "booking_requests",
        "status IN ('pending_review', 'confirmed', 'cancelled')",
    )
