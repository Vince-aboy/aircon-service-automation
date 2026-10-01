"""Create initial controlled-booking schema.

Revision ID: 20260930_0001
Revises:
Create Date: 2026-09-30
"""

from alembic import op
import sqlalchemy as sa


revision = "20260930_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("mobile", sa.String(length=20), nullable=False, unique=True),
        sa.Column("email", sa.String(length=254), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_table(
        "service_types",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False, unique=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.CheckConstraint("duration_minutes > 0", name="ck_service_types_positive_duration"),
    )
    op.create_table(
        "technicians",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("display_name", sa.String(length=120), nullable=False, unique=True),
        sa.Column("active", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.create_table(
        "addresses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("address_line", sa.String(length=255), nullable=False),
        sa.Column("barangay", sa.String(length=100), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("service_area_valid", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.create_table(
        "booking_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("reference_code", sa.String(length=24), nullable=False, unique=True),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("address_id", sa.Integer(), sa.ForeignKey("addresses.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("service_type_id", sa.Integer(), sa.ForeignKey("service_types.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("preferred_date", sa.Date(), nullable=False),
        sa.Column("preferred_window", sa.String(length=32), nullable=False),
        sa.Column("unit_count", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="pending_review", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("unit_count > 0", name="ck_booking_requests_positive_unit_count"),
        sa.CheckConstraint("status IN ('pending_review', 'confirmed', 'cancelled')", name="ck_booking_requests_status"),
    )
    op.create_table(
        "appointments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("booking_request_id", sa.Integer(), sa.ForeignKey("booking_requests.id", ondelete="RESTRICT"), nullable=False, unique=True),
        sa.Column("technician_id", sa.Integer(), sa.ForeignKey("technicians.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("scheduled_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scheduled_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="confirmed", nullable=False),
        sa.CheckConstraint("scheduled_end > scheduled_start", name="ck_appointments_valid_time_range"),
        sa.CheckConstraint("status IN ('confirmed', 'en_route', 'completed', 'cancelled')", name="ck_appointments_status"),
    )
    op.create_table(
        "appointment_status_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("appointment_id", sa.Integer(), sa.ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("from_status", sa.String(length=32), nullable=True),
        sa.Column("to_status", sa.String(length=32), nullable=False),
        sa.Column("actor_type", sa.String(length=32), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
    )
    op.create_table(
        "notification_outbox",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("booking_request_id", sa.Integer(), sa.ForeignKey("booking_requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("channel", sa.String(length=32), server_default="simulated", nullable=False),
        sa.Column("recipient_masked", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("payload", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("channel = 'simulated'", name="ck_notification_outbox_simulated_channel"),
        sa.CheckConstraint("status IN ('pending', 'recorded', 'failed')", name="ck_notification_outbox_status"),
    )


def downgrade() -> None:
    op.drop_table("notification_outbox")
    op.drop_table("appointment_status_history")
    op.drop_table("appointments")
    op.drop_table("booking_requests")
    op.drop_table("addresses")
    op.drop_table("technicians")
    op.drop_table("service_types")
    op.drop_table("customers")
