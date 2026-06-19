"""add project_id to sources

Lets a project be paused as a whole — its sources stop scraping. Backfills
existing tenant-level sources onto each tenant's single project (current state:
one project per tenant), so the pause filter has a project to key on.

Revision ID: 9a1b2c3d4e5f
Revises: 5f34e7049f71
Create Date: 2026-06-14 09:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9a1b2c3d4e5f"
down_revision: Union[str, None] = "5f34e7049f71"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("sources", sa.Column("project_id", sa.UUID(), nullable=True))
    op.create_index("ix_sources_project_id", "sources", ["project_id"])
    op.create_foreign_key(
        "fk_sources_project_id",
        "sources",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Backfill: attach each source to its tenant's project. Where a tenant has
    # exactly one project (current state), this is unambiguous. If a tenant has
    # multiple projects, pick the oldest as a safe default — admins can reassign.
    op.execute(
        """
        UPDATE sources s
           SET project_id = p.id
          FROM (
                SELECT DISTINCT ON (tenant_id) id, tenant_id
                  FROM projects
                 ORDER BY tenant_id, created_at ASC
               ) p
         WHERE p.tenant_id = s.tenant_id
           AND s.project_id IS NULL
        """
    )


def downgrade() -> None:
    op.drop_constraint("fk_sources_project_id", "sources", type_="foreignkey")
    op.drop_index("ix_sources_project_id", table_name="sources")
    op.drop_column("sources", "project_id")
