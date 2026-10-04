"""Add waitlisted booking requests.

Revision ID: 20261004_0009
Revises: 20261004_0008
"""

from alembic import op


revision = "20261004_0009"
down_revision = "20261004_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_booking_requests_status", "booking_requests", type_="check")
    op.create_check_constraint(
        "ck_booking_requests_status",
        "booking_requests",
        "status IN ('pending_review', 'waitlisted', 'approved_for_scheduling', 'scheduled', 'cancelled')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_booking_requests_status", "booking_requests", type_="check")
    op.create_check_constraint(
        "ck_booking_requests_status",
        "booking_requests",
        "status IN ('pending_review', 'approved_for_scheduling', 'scheduled', 'cancelled')",
    )
