"""Persist provider health and canonical website domains.

Revision ID: 20260907_provider_health_and_business_domain
Revises: 5d8a9c2b3e4f
Create Date: 2026-09-07
"""

from alembic import op
import sqlalchemy as sa


revision = "20260907_provider_health_and_business_domain"
down_revision = "5d8a9c2b3e4f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "provider_health" not in inspector.get_table_names():
        op.create_table(
            "provider_health",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("provider_name", sa.String(length=100), nullable=False, unique=True),
            sa.Column("state", sa.String(length=50), nullable=False, server_default="unknown"),
            sa.Column("message", sa.Text(), nullable=True),
            sa.Column("last_http_status", sa.Integer(), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_provider_health_provider_name", "provider_health", ["provider_name"])

    business_columns = {column["name"] for column in inspector.get_columns("businesses")}
    if "website_domain" not in business_columns:
        op.add_column("businesses", sa.Column("website_domain", sa.String(length=255), nullable=True))
    business_indexes = {index["name"] for index in inspector.get_indexes("businesses")}
    if "ix_businesses_website_domain" not in business_indexes:
        op.create_index("ix_businesses_website_domain", "businesses", ["website_domain"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "businesses" in inspector.get_table_names():
        indexes = {index["name"] for index in inspector.get_indexes("businesses")}
        if "ix_businesses_website_domain" in indexes:
            op.drop_index("ix_businesses_website_domain", table_name="businesses")
        columns = {column["name"] for column in inspector.get_columns("businesses")}
        if "website_domain" in columns:
            op.drop_column("businesses", "website_domain")
    if "provider_health" in inspector.get_table_names():
        op.drop_index("ix_provider_health_provider_name", table_name="provider_health")
        op.drop_table("provider_health")
