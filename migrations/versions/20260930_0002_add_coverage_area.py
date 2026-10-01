"""Add explicit prototype coverage area to service addresses.

Revision ID: 20260930_0002
Revises: 20260930_0001
Create Date: 2026-09-30
"""

from alembic import op
import sqlalchemy as sa


revision = "20260930_0002"
down_revision = "20260930_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "addresses",
        sa.Column(
            "coverage_area",
            sa.String(length=100),
            nullable=False,
            server_default="Urban Deca Homes, Tondo",
        ),
    )
    op.alter_column("addresses", "coverage_area", server_default=None)


def downgrade() -> None:
    op.drop_column("addresses", "coverage_area")
