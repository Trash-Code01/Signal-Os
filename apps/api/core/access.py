"""Shared-workspace authentication and server-enforced role policy."""
import os
import re
import jwt
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from .auth import SECRET_KEY, ALGORITHM
from .database import get_db
from .models import User

PUBLIC = {
    ("GET", "/api/health"),
    ("GET", "/api/auth/config"),
    ("POST", "/api/auth/google"),
    ("POST", "/api/auth/login"),
    ("GET", "/api/environment"),
    ("POST", "/api/setup-admin"),
    ("POST", "/api/webhooks/apollo"),
    ("GET", "/docs"),
    ("GET", "/openapi.json"),
    ("GET", "/redoc"),
}

def get_current_user(request: Request, db: Session = Depends(get_db)):
    header = request.headers.get("authorization", "")
    token = header[7:] if header.lower().startswith("bearer ") else request.cookies.get("access_token")
    try:
        payload = jwt.decode(token or "", SECRET_KEY, algorithms=[ALGORITHM], options={"require": ["exp", "sub", "ver"]})
        user = db.get(User, int(payload["sub"]))
        if not user or not user.is_active or user.session_version != payload["ver"] or user.role not in {"admin", "member", "viewer"}:
            raise ValueError()
    except (jwt.PyJWTError, ValueError, TypeError):
        raise HTTPException(401, "Session expired. Sign in with Google or password.")
    db.info["owner_id"] = user.id
    request.state.user = user
    return user

def authorize_request(request: Request, db: Session = Depends(get_db)):
    path = request.url.path.rstrip("/")
    if (request.method, path) in PUBLIC:
        return
    user = get_current_user(request, db)
    sensitive_get = path in {"/api/sync-sequences", "/api/debug-discovery"}
    mutating = request.method not in {"GET", "HEAD", "OPTIONS"} or sensitive_get
    if mutating and request.cookies.get("access_token"):
        configured = {value.strip().rstrip("/") for value in os.getenv("FRONTEND_ORIGIN", "").split(",") if value.strip()}
        defaults = {"http://localhost:3001", "http://127.0.0.1:3001", "http://localhost:3000", "http://127.0.0.1:3000", "https://devacia-frontend.onrender.com"}
        origins = configured | defaults
        req_origin = (request.headers.get("origin") or "").rstrip("/")
        if not req_origin and request.headers.get("referer"):
            from urllib.parse import urlparse
            p = urlparse(request.headers.get("referer"))
            if p.scheme and p.netloc:
                req_origin = f"{p.scheme}://{p.netloc}".rstrip("/")
        if not req_origin and request.headers.get("x-forwarded-host"):
            proto = request.headers.get("x-forwarded-proto", "https")
            req_origin = f"{proto}://{request.headers.get('x-forwarded-host')}".rstrip("/")
        is_render = req_origin.endswith(".onrender.com")
        if not req_origin or (req_origin not in origins and not is_render):
            raise HTTPException(403, "Invalid request origin")
    admin_only = path.startswith("/api/auth/users") or path.startswith("/api/migrate-") or path in {"/api/setup-admin", "/api/providers/status"} or sensitive_get or path.endswith("/permanent")
    if admin_only and user.role != "admin":
        raise HTTPException(403, "Admin access required")
    personal = path in {"/api/auth/preferences", "/api/auth/logout"}
    export = request.method == "POST" and re.fullmatch(r"/api/leads/\d+/export", path)
    if user.role == "viewer" and mutating and not personal and not export:
        raise HTTPException(403, "Viewer access is read-only")
    return user
