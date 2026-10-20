import os
import re
import socket
from . import runtime
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# PostgreSQL connection string
raw_url = os.environ.get("DATABASE_URL", "postgresql://devacia:devacia_password@localhost:5432/devacia_os")
if "channel_binding=" in raw_url:
    raw_url = re.sub(r"([?&])channel_binding=[^&]+(&|$)", r"\1", raw_url)
    raw_url = re.sub(r"[?&]$", "", raw_url)
    if "?" not in raw_url and "&" in raw_url:
        raw_url = raw_url.replace("&", "?", 1)

if raw_url.startswith("postgres://"):
    raw_url = raw_url.replace("postgres://", "postgresql+psycopg://", 1)
if raw_url.startswith("postgresql://"):
    raw_url = raw_url.replace("postgresql://", "postgresql+psycopg://", 1)
DATABASE_URL = raw_url

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite:") else {"connect_timeout": 15}
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args=connect_args,
    pool_timeout=15,
    pool_recycle=1800,
)

def _resolve_ipv4(host: str) -> str | None:
    try:
        infos = socket.getaddrinfo(host, None, socket.AF_INET)
        if infos:
            return infos[0][4][0]
    except Exception as exc:
        print(f"[database] IPv4 resolution failed for {host}: {exc}")
    return None

if not DATABASE_URL.startswith("sqlite:"):
    @event.listens_for(engine, "do_connect")
    def force_ipv4_hostaddr(dialect, conn_rec, cargs, cparams):
        # Render containers lack IPv6 outbound connectivity. Neon resolves to both
        # AAAA (IPv6) and A (IPv4). Passing hostaddr forces psycopg to connect over IPv4
        # while keeping the hostname for SSL SNI and cert verification.
        host = cparams.get("host")
        if host and host not in ("localhost", "127.0.0.1") and not host.startswith("/"):
            ipv4 = _resolve_ipv4(host)
            if ipv4:
                cparams["hostaddr"] = ipv4

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
