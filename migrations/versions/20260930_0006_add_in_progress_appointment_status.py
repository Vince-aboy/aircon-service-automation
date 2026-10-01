"""Add explicit in-progress status for local field work.

Revision ID: 20260930_0006
Revises: 20260930_0005
Create Date: 2026-09-30
"""

from alembic import op


revision = "20260930_0006"
down_revision = "20260930_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_appointments_status", "appointments", type_="check")
    op.create_check_constraint(
        "ck_appointments_status",
        "appointments",
        "status IN ('confirmed', 'en_route', 'in_progress', 'completed', 'cancelled')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_appointments_status", "appointments", type_="check")
    op.create_check_constraint(
        "ck_appointments_status",
        "appointments",
        "status IN ('confirmed', 'en_route', 'completed', 'cancelled')",
    )
