"""legacy schema baseline

This placeholder records the schema revision already present in deployed
databases. Its migration was not retained in the repository, so it performs no
DDL; the CRM revision follows it and contains its own idempotent checks.

Revision ID: c46cabb41464
Revises:
Create Date: 2026-08-19
"""


revision = "c46cabb41464"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
