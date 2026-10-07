"""Allow the automation outbox to carry shared operational jobs.

Revision ID: 20261008_0013
Revises: 20261007_0012
"""

from alembic import op
import sqlalchemy as sa


revision = "20261008_0013"
down_revision = "20261007_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("notification_outbox", recreate="always") as batch:
        batch.alter_column(
            "booking_request_id",
            existing_type=sa.Integer(),
            nullable=True,
        )
        batch.add_column(sa.Column("operational_job_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_notification_outbox_operational_job_id",
            "operational_jobs",
            ["operational_job_id"],
            ["id"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    with op.batch_alter_table("notification_outbox", recreate="always") as batch:
        batch.drop_constraint("fk_notification_outbox_operational_job_id", type_="foreignkey")
        batch.drop_column("operational_job_id")
        batch.alter_column(
            "booking_request_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
