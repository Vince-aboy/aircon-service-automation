"""Allow cancelled appointment slots to be reused.

Revision ID: 20261004_0008
Revises: 20261001_0007
"""

from alembic import op
import sqlalchemy as sa


revision = "20261004_0008"
down_revision = "20261001_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("uq_appointments_team_scheduled_start", "appointments", type_="unique")
    op.create_index(
        "uq_appointments_active_team_scheduled_start",
        "appointments",
        ["service_team_id", "scheduled_start"],
        unique=True,
        postgresql_where=sa.text("status <> 'cancelled'"),
        sqlite_where=sa.text("status <> 'cancelled'"),
    )


def downgrade() -> None:
    op.drop_index("uq_appointments_active_team_scheduled_start", table_name="appointments")
    op.create_unique_constraint(
        "uq_appointments_team_scheduled_start",
        "appointments",
        ["service_team_id", "scheduled_start"],
    )
