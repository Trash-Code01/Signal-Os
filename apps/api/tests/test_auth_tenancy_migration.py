import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


def _load_revision():
    path = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "20260919_google_auth_tenancy.py"
    spec = importlib.util.spec_from_file_location("auth_tenancy_revision", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_auth_tenancy_revision_is_additive_and_idempotent():
    engine = sa.create_engine("sqlite://")
    metadata = sa.MetaData()
    sa.Table(
        "users",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
    )
    sa.Table(
        "businesses",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
    )
    metadata.create_all(engine)

    revision = _load_revision()
    with engine.begin() as connection:
        revision.op = Operations(MigrationContext.configure(connection))
        revision.upgrade()
        revision.upgrade()
        inspector = sa.inspect(connection)
        user_columns = {column["name"] for column in inspector.get_columns("users")}
        business_columns = {column["name"] for column in inspector.get_columns("businesses")}
        assert {"google_sub", "role", "is_active", "session_version", "personal_email_enabled", "phone_enabled"} <= user_columns
        assert "owner_id" in business_columns
        assert "ux_users_google_sub" in {index["name"] for index in inspector.get_indexes("users")}
        assert "ix_businesses_owner_id" in {index["name"] for index in inspector.get_indexes("businesses")}
        connection.execute(sa.text("INSERT INTO users (id, email, hashed_password) VALUES (1, 'owner@example.com', '!')"))
        connection.execute(sa.text("INSERT INTO businesses (id, name, owner_id) VALUES (1, 'Private', 1)"))
        assert connection.execute(sa.text("SELECT role FROM users WHERE id = 1")).scalar_one() == "viewer"
