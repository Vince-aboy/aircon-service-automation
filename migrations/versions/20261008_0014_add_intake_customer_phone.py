"""Store team-intake customer names and phone numbers as job fields."""

from alembic import op
import sqlalchemy as sa


revision = "20261008_0014"
down_revision = "20261008_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("schedule_intake_items", sa.Column("customer_phone", sa.String(length=32), nullable=True))
    op.add_column("operational_jobs", sa.Column("customer_phone", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("operational_jobs", "customer_phone")
    op.drop_column("schedule_intake_items", "customer_phone")
