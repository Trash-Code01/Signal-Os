"""add the in-app CRM workspace tables

Revision ID: 20260819_crm_workspace
Revises:
Create Date: 2026-08-19
"""

from alembic import op
import sqlalchemy as sa


revision = "20260819_crm_workspace"
down_revision = "c46cabb41464"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "crm_leads" not in inspector.get_table_names():
        op.create_table(
            "crm_leads",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("business_id", sa.Integer(), nullable=False),
            sa.Column("stage", sa.String(length=50), nullable=False, server_default="new"),
            sa.Column("owner_name", sa.String(length=255), nullable=True),
            sa.Column("tags", sa.JSON(), nullable=True),
            sa.Column("source", sa.String(length=50), nullable=False, server_default="campaign"),
            sa.Column("next_follow_up_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_contacted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["business_id"], ["businesses.id"]),
            sa.UniqueConstraint("business_id"),
        )
        op.create_index("ix_crm_leads_business_id", "crm_leads", ["business_id"])
        op.create_index("ix_crm_leads_stage", "crm_leads", ["stage"])
    if "crm_activities" not in inspector.get_table_names():
        op.create_table(
            "crm_activities",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("business_id", sa.Integer(), nullable=False),
            sa.Column("activity_type", sa.String(length=50), nullable=False, server_default="note"),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("created_by", sa.String(length=100), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["business_id"], ["businesses.id"]),
        )
        op.create_index("ix_crm_activities_business_id", "crm_activities", ["business_id"])


def downgrade() -> None:
    op.drop_index("ix_crm_activities_business_id", table_name="crm_activities")
    op.drop_table("crm_activities")
    op.drop_index("ix_crm_leads_stage", table_name="crm_leads")
    op.drop_index("ix_crm_leads_business_id", table_name="crm_leads")
    op.drop_table("crm_leads")
