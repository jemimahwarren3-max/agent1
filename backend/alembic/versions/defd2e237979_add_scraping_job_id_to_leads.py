"""add scraping_job_id to leads

Revision ID: defd2e237979
Revises: ec646f2d277b
Create Date: 2026-11-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "defd2e237979"
down_revision: Union[str, None] = "ec646f2d277b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "leads",
        sa.Column("scraping_job_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_leads_scraping_job_id", "leads", ["scraping_job_id"])
    op.create_foreign_key(
        "fk_leads_scraping_job_id",
        "leads",
        "scraping_jobs",
        ["scraping_job_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_leads_scraping_job_id", "leads", type_="foreignkey")
    op.drop_index("ix_leads_scraping_job_id", table_name="leads")
    op.drop_column("leads", "scraping_job_id")
