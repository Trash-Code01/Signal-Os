import os
from datetime import timedelta
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from google.oauth2 import id_token
from google.auth.transport.requests import Request as GoogleRequest
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from core.access import get_current_user
from core.auth import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, get_password_hash, verify_password
from core.database import get_db
from core.models import User
from core.runtime import IS_STAGING

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
Role = Literal["admin", "member", "viewer"]

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    name: str | None = None
    role: Role
    is_active: bool
    personal_email_enabled: bool
    phone_enabled: bool
    model_config = {"from_attributes": True}

class GoogleLogin(BaseModel):
    credential: str = Field(min_length=1, max_length=12000)
    nonce: str = Field(min_length=20, max_length=200)

class Invite(BaseModel):
    email: EmailStr
    role: Role = "admin"

class UpdateUser(BaseModel):
    role: Role
    is_active: bool

class Preferences(BaseModel):
    personal_email_enabled: bool = False
    phone_enabled: bool = False


def commit(db):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Account already exists. Refresh and try again.")

@router.get("/config")
def config():
    return {"client_id": os.getenv("GOOGLE_CLIENT_ID", "")}

@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    email = str(req.email).strip().lower()
    user = db.query(User).filter(func.lower(User.email) == email).first()

    # Bootstrap default admin if logging in with default credentials and user does not exist
    if not user and email == "admin@devacia.com" and req.password == "admin123":
        user = User(
            email=email,
            hashed_password=get_password_hash("admin123"),
            name="Devacia Administrator",
            role="admin",
            is_active=True
        )
        db.add(user)
        commit(db)
        db.refresh(user)

    # Auto-register any new email/password account so other accounts have full access to APIs & pipeline
    if not user and len(req.password) >= 4:
        user = User(
            email=email,
            hashed_password=get_password_hash(req.password),
            name=email.split("@")[0].replace(".", " ").replace("_", " ").title(),
            role="admin",
            is_active=True
        )
        db.add(user)
        commit(db)
        db.refresh(user)

    if not user:
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    if user and user.hashed_password == "!google-only" and IS_STAGING and len(req.password) >= 4:
        user.hashed_password = get_password_hash(req.password)
        commit(db)
        db.refresh(user)

    if not user.hashed_password or not verify_password(req.password, user.hashed_password):
        if user.hashed_password == "!google-only":
            raise HTTPException(status_code=400, detail="This account is set up with Google Sign-In. Please click Continue with Google.")
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    if user.is_active is False:
        raise HTTPException(status_code=403, detail="Your account has been disabled.")

    token = create_access_token(
        {"sub": str(user.id), "ver": user.session_version},
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "email": user.email,
        "role": user.role,
        "name": user.name
    }

@router.post("/google")
def google_login(body: GoogleLogin, db: Session = Depends(get_db)):
    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    if not client_id and not (IS_STAGING and body.credential.startswith("dev-mock:")):
        raise HTTPException(503, "Google sign-in is not configured yet. Contact your admin.")

    claims = None
    if IS_STAGING and body.credential.startswith("dev-mock:"):
        mock_email = body.credential.split(":", 1)[1].strip().lower()
        if not mock_email or "@" not in mock_email:
            mock_email = "devacia.com@gmail.com"
        claims = {
            "iss": "accounts.google.com",
            "email_verified": True,
            "nonce": body.nonce,
            "sub": f"mock-google-{mock_email}",
            "email": mock_email,
            "name": mock_email.split("@")[0].replace(".", " ").title(),
        }
    else:
        try:
            claims = id_token.verify_oauth2_token(body.credential, GoogleRequest(), client_id)
            if claims.get("iss") not in {"accounts.google.com", "https://accounts.google.com"} or claims.get("email_verified") is not True or claims.get("nonce") != body.nonce or not claims.get("sub"):
                raise ValueError()
        except ValueError:
            raise HTTPException(401, "Google sign-in could not be verified. Try again.")
        except Exception:
            raise HTTPException(503, "Google verification is temporarily unavailable. Try again.")
    email = str(claims.get("email", "")).strip().lower()
    user = db.query(User).filter(User.google_sub == claims["sub"]).first()
    if not user:
        if not (email.endswith("@gmail.com") or claims.get("hd")):
            raise HTTPException(403, "Use a Gmail or Google Workspace account for this invitation.")
        user = db.query(User).filter(func.lower(User.email) == email).first()
        if user and user.google_sub:
            raise HTTPException(403, "This invitation is linked to another Google account.")
        # Auto-create user with full admin access so other Google accounts have complete pipeline access
        if not user:
            user = User(
                email=email,
                hashed_password="!google-only",
                role="admin",
                name=str(claims.get("name", ""))[:255] or email.split("@")[0],
                is_active=True
            )
            db.add(user)
        if user.is_active is False:
            raise HTTPException(403, "Your account has been disabled.")
        user.google_sub = claims["sub"]
    if user.is_active is False:
        raise HTTPException(403, "Your account has been disabled.")
    user.name = str(claims.get("name", ""))[:255]
    commit(db)
    db.refresh(user)
    token = create_access_token({"sub": str(user.id), "ver": user.session_version}, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return {"access_token": token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return user

@router.post("/logout")
def logout(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user.session_version += 1
    commit(db)
    return {"success": True}

@router.put("/preferences", response_model=UserResponse)
def preferences(body: Preferences, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user.personal_email_enabled = body.personal_email_enabled
    user.phone_enabled = body.phone_enabled
    commit(db)
    return user


def admin(user: User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(403, "Admin access required")
    return user

@router.get("/users", response_model=list[UserResponse])
def users(_: User = Depends(admin), db: Session = Depends(get_db)):
    return db.query(User).order_by(User.id).all()

@router.post("/users", response_model=UserResponse, status_code=201)
def invite(body: Invite, _: User = Depends(admin), db: Session = Depends(get_db)):
    email = str(body.email).lower()
    if db.query(User).filter(func.lower(User.email) == email).first():
        raise HTTPException(409, "This email already has workspace access. Edit its role instead.")
    user = User(email=email, hashed_password="!google-only", role=body.role)
    db.add(user)
    commit(db)
    db.refresh(user)
    return user

@router.patch("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: int, body: UpdateUser, actor: User = Depends(admin), db: Session = Depends(get_db)):
    if actor.id == user_id and (body.role != "admin" or not body.is_active):
        raise HTTPException(400, "You cannot remove your own admin access.")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    user.role, user.is_active = body.role, body.is_active
    user.session_version += 1
    commit(db)
    return user
