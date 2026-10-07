"""Add the shared operational job layer.

Revision ID: 20261007_0012
Revises: 20261007_0011
"""

from alembic import op
import sqlalchemy as sa


revision = "20261007_0012"
down_revision = "20261007_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "operational_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("booking_request_id", sa.Integer(), sa.ForeignKey("booking_requests.id", ondelete="RESTRICT"), nullable=True, unique=True),
        sa.Column("schedule_intake_item_id", sa.Integer(), sa.ForeignKey("schedule_intake_items.id", ondelete="RESTRICT"), nullable=True, unique=True),
        sa.Column("appointment_id", sa.Integer(), sa.ForeignKey("appointments.id", ondelete="RESTRICT"), nullable=True, unique=True),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("customer_label", sa.String(length=120), nullable=False),
        sa.Column("customer_is_provisional", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("address_label", sa.String(length=255), nullable=False),
        sa.Column("service_type_id", sa.Integer(), sa.ForeignKey("service_types.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("service_label", sa.String(length=255), nullable=False),
        sa.Column("service_team_id", sa.Integer(), sa.ForeignKey("service_teams.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("scheduled_date", sa.Date(), nullable=True),
        sa.Column("scheduled_time", sa.Time(), nullable=True),
        sa.Column("price", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending_review"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("source IN ('customer_booking', 'team_intake')", name="ck_operational_jobs_source"),
        sa.CheckConstraint("status IN ('pending_review', 'waitlisted', 'approved_for_scheduling', 'scheduled', 'confirmed', 'en_route', 'in_progress', 'completed', 'cancelled')", name="ck_operational_jobs_status"),
        sa.CheckConstraint("price IS NULL OR price >= 0", name="ck_operational_jobs_nonnegative_price"),
        sa.CheckConstraint("(booking_request_id IS NOT NULL) <> (schedule_intake_item_id IS NOT NULL)", name="ck_operational_jobs_one_source"),
    )
    op.create_index("ix_operational_jobs_scheduled_date", "operational_jobs", ["scheduled_date"])
    op.create_index("ix_operational_jobs_status", "operational_jobs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_operational_jobs_status", table_name="operational_jobs")
    op.drop_index("ix_operational_jobs_scheduled_date", table_name="operational_jobs")
    op.drop_table("operational_jobs")
