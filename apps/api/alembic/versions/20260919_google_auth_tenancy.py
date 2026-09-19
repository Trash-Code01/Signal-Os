"""Add Google accounts, roles, lookup preferences and account ownership.

Revision ID: 20260919_google_auth_tenancy
Revises: 20260907_provider_health_and_business_domain
Create Date: 2026-09-19

Legacy business rows intentionally keep owner_id NULL. They remain invisible
until an operator assigns each connected record graph to a verified account.
"""

from alembic import op
import sqlalchemy as sa


revision = "20260919_google_auth_tenancy"
down_revision = "20260907_provider_health_and_business_domain"
branch_labels = None
depends_on = None


OWNED_TABLES = (
    "industry_configs",
    "devacia_offers",
    "campaigns",
    "campaign_locations",
    "job_runs",
    "businesses",
    "business_sources",
    "websites",
    "website_pages",
    "website_technologies",
    "website_screenshots",
    "website_audits",
    "website_evidence",
    "social_profiles",
    "decision_makers",
    "scores",
    "opportunities",
    "ai_analyses",
    "crm_leads",
    "crm_activities",
    "crm_notes",
    "exports",
)


def _user_columns() -> tuple[sa.Column, ...]:
    return (
        sa.Column("google_sub", sa.String(length=255), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("role", sa.String(length=20), nullable=False, server_default="viewer"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("session_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("personal_email_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("phone_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now()),
    )


def _columns(inspector: sa.Inspector, table: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table)}


def _indexes(inspector: sa.Inspector, table: str) -> set[str]:
    return {index["name"] for index in inspector.get_indexes(table)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "users" in tables:
        user_columns = _columns(inspector, "users")
        for column in _user_columns():
            if column.name not in user_columns:
                op.add_column("users", column)
        inspector = sa.inspect(bind)
        if "ux_users_google_sub" not in _indexes(inspector, "users"):
            op.create_index("ux_users_google_sub", "users", ["google_sub"], unique=True)

    if "users" not in tables:
        return

    for table in OWNED_TABLES:
        if table not in tables:
            continue
        inspector = sa.inspect(bind)
        if "owner_id" not in _columns(inspector, table):
            if bind.dialect.name == "sqlite":
                op.execute(sa.text(f'ALTER TABLE "{table}" ADD COLUMN owner_id INTEGER REFERENCES users(id)'))
            else:
                op.add_column(
                    table,
                    sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
                )
        inspector = sa.inspect(bind)
        index_name = f"ix_{table}_owner_id"
        if index_name not in _indexes(inspector, table):
            op.create_index(index_name, table, ["owner_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    for table in reversed(OWNED_TABLES):
        if table not in tables:
            continue
        inspector = sa.inspect(bind)
        index_name = f"ix_{table}_owner_id"
        if index_name in _indexes(inspector, table):
            op.drop_index(index_name, table_name=table)
        if "owner_id" not in _columns(inspector, table):
            continue
        for constraint in inspector.get_foreign_keys(table):
            if constraint.get("constrained_columns") == ["owner_id"] and constraint.get("name"):
                op.drop_constraint(constraint["name"], table, type_="foreignkey")
        op.drop_column(table, "owner_id")

    if "users" not in tables:
        return
    inspector = sa.inspect(bind)
    if "ux_users_google_sub" in _indexes(inspector, "users"):
        op.drop_index("ux_users_google_sub", table_name="users")
    for column in reversed(_user_columns()):
        inspector = sa.inspect(bind)
        if column.name in _columns(inspector, "users"):
            op.drop_column("users", column.name)
