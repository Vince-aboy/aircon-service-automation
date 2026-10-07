"""Add provisional customer labels to schedule intake rows.

Revision ID: 20261007_0011
Revises: 20261007_0010
"""

from alembic import op
import sqlalchemy as sa


revision = "20261007_0011"
down_revision = "20261007_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "schedule_intake_items",
        sa.Column("customer_is_provisional", sa.Boolean(), server_default="false", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("schedule_intake_items", "customer_is_provisional")
