import os
from . import runtime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# PostgreSQL connection string
raw_url = os.environ.get("DATABASE_URL", "postgresql://devacia:devacia_password@localhost:5432/devacia_os")
if raw_url.startswith("postgres://"):
    raw_url = raw_url.replace("postgres://", "postgresql+psycopg://", 1)
if raw_url.startswith("postgresql://"):
    raw_url = raw_url.replace("postgresql://", "postgresql+psycopg://", 1)
DATABASE_URL = raw_url

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite:") else {"connect_timeout": 10}
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args=connect_args,
    pool_timeout=15,
    pool_recycle=1800,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
