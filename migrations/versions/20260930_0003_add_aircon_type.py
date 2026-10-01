"""Add selected aircon type to booking requests.

Revision ID: 20260930_0003
Revises: 20260930_0002
Create Date: 2026-09-30
"""

from alembic import op
import sqlalchemy as sa


revision = "20260930_0003"
down_revision = "20260930_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "booking_requests",
        sa.Column("aircon_type", sa.String(length=64), nullable=False, server_default="Window Type"),
    )
    op.execute("UPDATE service_types SET name = 'Aircon Cleaning' WHERE name = 'Basic Split-Type Cleaning'")
    op.alter_column("booking_requests", "aircon_type", server_default=None)


def downgrade() -> None:
    op.execute("UPDATE service_types SET name = 'Basic Split-Type Cleaning' WHERE name = 'Aircon Cleaning'")
    op.drop_column("booking_requests", "aircon_type")
