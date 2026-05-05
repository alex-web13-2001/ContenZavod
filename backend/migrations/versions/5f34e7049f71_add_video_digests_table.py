"""add_video_digests_table

Revision ID: 5f34e7049f71
Revises: 46aa0bf4cbd4
Create Date: 2026-05-04 20:15:24.370989
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '5f34e7049f71'
down_revision: Union[str, None] = '46aa0bf4cbd4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('video_digests',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('project_id', sa.UUID(), nullable=False),
    sa.Column('title', sa.String(length=500), nullable=False),
    sa.Column('script_text', sa.Text(), nullable=True),
    sa.Column('language', sa.String(length=10), nullable=False),
    sa.Column('material_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('revid_pid', sa.String(length=100), nullable=True),
    sa.Column('revid_status', sa.String(length=30), nullable=False),
    sa.Column('video_url', sa.Text(), nullable=True),
    sa.Column('thumbnail_url', sa.Text(), nullable=True),
    sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('duration_seconds', sa.Integer(), nullable=True),
    sa.Column('credits_used', sa.Integer(), nullable=True),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_video_digests_project_id'), 'video_digests', ['project_id'], unique=False)
    op.create_index(op.f('ix_video_digests_revid_status'), 'video_digests', ['revid_status'], unique=False)
    op.create_index(op.f('ix_video_digests_tenant_id'), 'video_digests', ['tenant_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_video_digests_tenant_id'), table_name='video_digests')
    op.drop_index(op.f('ix_video_digests_revid_status'), table_name='video_digests')
    op.drop_index(op.f('ix_video_digests_project_id'), table_name='video_digests')
    op.drop_table('video_digests')
