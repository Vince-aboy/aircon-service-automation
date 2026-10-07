"""Add raw schedule intake staging tables.

Revision ID: 20261007_0010
Revises: 20261004_0009
"""

from alembic import op
import sqlalchemy as sa


revision = "20261007_0010"
down_revision = "20261004_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "schedule_intakes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("schedule_date", sa.Date(), nullable=False),
        sa.Column("raw_message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="draft", nullable=False),
        sa.Column("source", sa.String(length=32), server_default="manual_paste", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "status IN ('draft', 'ready', 'confirmed', 'cancelled')",
            name="ck_schedule_intakes_status",
        ),
        sa.CheckConstraint("source = 'manual_paste'", name="ck_schedule_intakes_manual_source"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_schedule_intakes_schedule_date", "schedule_intakes", ["schedule_date"])

    op.create_table(
        "schedule_intake_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("schedule_intake_id", sa.Integer(), nullable=False),
        sa.Column("source_line", sa.Text(), nullable=True),
        sa.Column("service_team_id", sa.Integer(), nullable=True),
        sa.Column("customer_id", sa.Integer(), nullable=True),
        sa.Column("customer_name", sa.String(length=120), nullable=True),
        sa.Column("service_type_id", sa.Integer(), nullable=True),
        sa.Column("raw_service_text", sa.String(length=255), nullable=True),
        sa.Column("building_number", sa.Integer(), nullable=True),
        sa.Column("unit_number", sa.String(length=32), nullable=True),
        sa.Column("scheduled_time", sa.Time(), nullable=True),
        sa.Column("price", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("review_status", sa.String(length=32), server_default="needs_review", nullable=False),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("booking_request_id", sa.Integer(), nullable=True),
        sa.Column("appointment_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "building_number IS NULL OR building_number > 0",
            name="ck_schedule_items_positive_building",
        ),
        sa.CheckConstraint("price IS NULL OR price >= 0", name="ck_schedule_items_nonnegative_price"),
        sa.CheckConstraint(
            "review_status IN ('needs_review', 'ready', 'confirmed', 'skipped')",
            name="ck_schedule_items_review_status",
        ),
        sa.ForeignKeyConstraint(["appointment_id"], ["appointments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["booking_request_id"], ["booking_requests.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["schedule_intake_id"], ["schedule_intakes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["service_team_id"], ["service_teams.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["service_type_id"], ["service_types.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("appointment_id"),
        sa.UniqueConstraint("booking_request_id"),
    )
    op.create_index("ix_schedule_intake_items_intake_id", "schedule_intake_items", ["schedule_intake_id"])
    op.create_index("ix_schedule_intake_items_review_status", "schedule_intake_items", ["review_status"])


def downgrade() -> None:
    op.drop_index("ix_schedule_intake_items_review_status", table_name="schedule_intake_items")
    op.drop_index("ix_schedule_intake_items_intake_id", table_name="schedule_intake_items")
    op.drop_table("schedule_intake_items")
    op.drop_index("ix_schedule_intakes_schedule_date", table_name="schedule_intakes")
    op.drop_table("schedule_intakes")
