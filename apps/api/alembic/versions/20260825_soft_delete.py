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
    # Add deleted_at to campaigns
    op.add_column('campaigns', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f('ix_campaigns_deleted_at'), 'campaigns', ['deleted_at'], unique=False)
    
    # Add deleted_at to businesses
    op.add_column('businesses', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f('ix_businesses_deleted_at'), 'businesses', ['deleted_at'], unique=False)
    
    # Add deleted_at to crm_leads
    op.add_column('crm_leads', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f('ix_crm_leads_deleted_at'), 'crm_leads', ['deleted_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_crm_leads_deleted_at'), table_name='crm_leads')
    op.drop_column('crm_leads', 'deleted_at')
    
    op.drop_index(op.f('ix_businesses_deleted_at'), table_name='businesses')
    op.drop_column('businesses', 'deleted_at')
    
    op.drop_index(op.f('ix_campaigns_deleted_at'), table_name='campaigns')
    op.drop_column('campaigns', 'deleted_at')
