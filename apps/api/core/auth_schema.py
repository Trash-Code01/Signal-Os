"""Idempotent additive auth migration for existing PostgreSQL/SQLite stores."""
from sqlalchemy import inspect, text
from .models import User

def migrate_auth_schema(engine):
    User.__table__.create(engine, checkfirst=True)
    columns = {column["name"] for column in inspect(engine).get_columns("users")}
    additions = {
        "hashed_password": "VARCHAR(255) NOT NULL DEFAULT '!no-password'",
        "created_at": "TIMESTAMP",
        "google_sub": "VARCHAR(255)", "name": "VARCHAR(255)",
        "role": "VARCHAR(20) NOT NULL DEFAULT 'viewer'",
        "is_active": "BOOLEAN NOT NULL DEFAULT TRUE",
        "session_version": "INTEGER NOT NULL DEFAULT 0",
        "personal_email_enabled": "BOOLEAN NOT NULL DEFAULT FALSE",
        "phone_enabled": "BOOLEAN NOT NULL DEFAULT FALSE",
    }
    with engine.begin() as conn:
        for name, definition in additions.items():
            if name not in columns:
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {name} {definition}"))
        conn.execute(text("UPDATE users SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL"))
        if engine.dialect.name == "postgresql":
            conn.execute(text("ALTER TABLE users ALTER COLUMN created_at SET DEFAULT NOW()"))
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_google_sub ON users (google_sub)"))
