"""Add the two-team dispatcher-board foundation.

Revision ID: 20260930_0005
Revises: 20260930_0004
Create Date: 2026-09-30
"""

from alembic import op
import sqlalchemy as sa


revision = "20260930_0005"
down_revision = "20260930_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_booking_requests_status", "booking_requests", type_="check")
    op.create_check_constraint(
        "ck_booking_requests_status",
        "booking_requests",
        "status IN ('pending_review', 'approved_for_scheduling', 'scheduled', 'cancelled')",
    )
    op.create_table(
        "service_teams",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=80), nullable=False, unique=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.create_table(
        "team_memberships",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("service_team_id", sa.Integer(), sa.ForeignKey("service_teams.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("technician_id", sa.Integer(), sa.ForeignKey("technicians.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("is_lead", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.UniqueConstraint("service_team_id", "technician_id", name="uq_team_memberships_team_technician"),
    )
    op.add_column("appointments", sa.Column("service_team_id", sa.Integer(), nullable=False))
    op.create_foreign_key(
        "fk_appointments_service_team",
        "appointments",
        "service_teams",
        ["service_team_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint("uq_appointments_team_scheduled_start", "appointments", ["service_team_id", "scheduled_start"])


def downgrade() -> None:
    op.drop_constraint("uq_appointments_team_scheduled_start", "appointments", type_="unique")
    op.drop_constraint("fk_appointments_service_team", "appointments", type_="foreignkey")
    op.drop_column("appointments", "service_team_id")
    op.drop_table("team_memberships")
    op.drop_table("service_teams")
    op.drop_constraint("ck_booking_requests_status", "booking_requests", type_="check")
    op.create_check_constraint(
        "ck_booking_requests_status",
        "booking_requests",
        "status IN ('pending_review', 'approved_for_scheduling', 'cancelled')",
    )
