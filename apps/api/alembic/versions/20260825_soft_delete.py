"""Add deleted_at for soft delete

Revision ID: 5d8a9c2b3e4f
Revises: 20260819_crm_workspace
Create Date: 2026-08-25 23:59:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5d8a9c2b3e4f'
down_revision: Union[str, None] = '20260819_crm_workspace'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    campaign_cols = {c["name"] for c in inspector.get_columns("campaigns")}
    if "deleted_at" not in campaign_cols:
        op.add_column('campaigns', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    campaign_indexes = {idx["name"] for idx in inspector.get_indexes("campaigns")}
    if "ix_campaigns_deleted_at" not in campaign_indexes:
        op.create_index(op.f('ix_campaigns_deleted_at'), 'campaigns', ['deleted_at'], unique=False)

    biz_cols = {c["name"] for c in inspector.get_columns("businesses")}
    if "deleted_at" not in biz_cols:
        op.add_column('businesses', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    biz_indexes = {idx["name"] for idx in inspector.get_indexes("businesses")}
    if "ix_businesses_deleted_at" not in biz_indexes:
        op.create_index(op.f('ix_businesses_deleted_at'), 'businesses', ['deleted_at'], unique=False)

    crm_cols = {c["name"] for c in inspector.get_columns("crm_leads")}
    if "deleted_at" not in crm_cols:
        op.add_column('crm_leads', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    crm_indexes = {idx["name"] for idx in inspector.get_indexes("crm_leads")}
    if "ix_crm_leads_deleted_at" not in crm_indexes:
        op.create_index(op.f('ix_crm_leads_deleted_at'), 'crm_leads', ['deleted_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_crm_leads_deleted_at'), table_name='crm_leads')
    op.drop_column('crm_leads', 'deleted_at')
    
    op.drop_index(op.f('ix_businesses_deleted_at'), table_name='businesses')
    op.drop_column('businesses', 'deleted_at')
    
    op.drop_index(op.f('ix_campaigns_deleted_at'), table_name='campaigns')
    op.drop_column('campaigns', 'deleted_at')
