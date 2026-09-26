"""Load an explicitly selected environment before database/provider imports."""
import os
import secrets
from pathlib import Path
from dotenv import load_dotenv

API_ROOT = Path(__file__).resolve().parents[1]
explicit_discovery = os.getenv("DISCOVERY_MODE")
if os.getenv("APP_ENV_FILE"):
    load_dotenv(os.environ["APP_ENV_FILE"], override=True)

# Use one fail-closed environment decision everywhere. An unspecified SQLite
# runtime is staging so it cannot accidentally use inherited live credentials.
configured_database_url = os.getenv("DATABASE_URL", "").strip().lower()
was_unlabelled = not os.getenv("ENVIRONMENT") and not os.getenv("APP_ENV_FILE")
RUNTIME_ENVIRONMENT = os.getenv("ENVIRONMENT", "").strip().lower()
if not RUNTIME_ENVIRONMENT:
    is_render = bool(os.getenv("RENDER") or os.getenv("RENDER_SERVICE_ID"))
    RUNTIME_ENVIRONMENT = "production" if is_render else "staging"
os.environ["ENVIRONMENT"] = RUNTIME_ENVIRONMENT

IS_STAGING = RUNTIME_ENVIRONMENT == "staging"
if IS_STAGING:
    load_dotenv(API_ROOT / ".env.staging.local", override=True)
    os.environ["ENVIRONMENT"] = RUNTIME_ENVIRONMENT
    os.environ["DATABASE_URL"] = "sqlite:///" + (API_ROOT / "staging.db").as_posix()
    if was_unlabelled or not (explicit_discovery or os.getenv("DISCOVERY_MODE")):
        os.environ["DISCOVERY_MODE"] = "mock"
    elif explicit_discovery:
        os.environ["DISCOVERY_MODE"] = explicit_discovery

    secret_file = API_ROOT / ".staging-session-key"
    if not secret_file.exists():
        try:
            with secret_file.open("x") as handle:
                handle.write(secrets.token_urlsafe(48))
        except FileExistsError:
            pass
    os.environ["JWT_SECRET_KEY"] = secret_file.read_text().strip()
