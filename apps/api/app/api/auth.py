from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Response, Request, status
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password, verify_password, generate_session_token, verify_session_token
from app.db.deps import get_db
from app.db.models import Merchant, User

router = APIRouter(tags=["auth"])

SESSION_COOKIE_NAME = "reclaim_session"


class SignUpRequest(BaseModel):
    email: str
    password: str
    merchant_name: Optional[str] = "Demo Merchant Inc."

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        cleaned = v.lower().strip()
        if "@" not in cleaned or "." not in cleaned.split("@")[-1] or len(cleaned) < 5:
            raise ValueError("Invalid email address format")
        return cleaned


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        cleaned = v.lower().strip()
        if "@" not in cleaned or "." not in cleaned.split("@")[-1] or len(cleaned) < 5:
            raise ValueError("Invalid email address format")
        return cleaned


class UserResponse(BaseModel):
    id: int
    merchant_id: int
    merchant_name: str
    email: str
    created_at: str


def _set_session_cookie(request: Request, response: Response, token: str) -> None:
    is_secure = request.url.scheme == "https" or getattr(settings, "app_env", "development").lower() == "production"
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=is_secure,
        max_age=86400 * 7,  # 7 days
    )


@router.post("/auth/signup")
def signup(req: SignUpRequest, request: Request, response: Response, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Create a new merchant operator user account."""
    if len(req.password.strip()) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters long",
        )

    existing_user = db.execute(
        select(User).where(User.email == req.email.lower().strip())
    ).scalars().first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists",
        )

    # Create custom merchant if name provided, otherwise use default merchant
    if req.merchant_name and req.merchant_name.strip() and req.merchant_name.strip() != "Demo Merchant Inc.":
        merchant = Merchant(
            name=req.merchant_name.strip(),
            metadata_json={"auth": True},
        )
        db.add(merchant)
        db.commit()
        db.refresh(merchant)
    else:
        merchant_id = settings.razorpay_merchant_id
        merchant = db.get(Merchant, merchant_id)
        if merchant is None:
            merchant = Merchant(
                id=merchant_id,
                name="Demo Merchant Inc.",
                metadata_json={"auth": True},
            )
            db.add(merchant)
            db.commit()
            db.refresh(merchant)

    user = User(
        merchant_id=merchant.id,

        email=req.email.lower().strip(),
        password_hash=hash_password(req.password),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = generate_session_token(user.id)
    _set_session_cookie(request, response, token)

    # Security: Token is NEVER returned in the JSON response payload.
    # The browser relies exclusively on the HTTP-only cookie.
    return {
        "status": "success",
        "message": "Account created successfully",
        "user": {
            "id": user.id,
            "merchant_id": user.merchant_id,
            "merchant_name": merchant.name,
            "email": user.email,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
    }


@router.post("/auth/login")
def login(req: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Authenticate merchant operator user and issue secure session cookie."""
    user = db.execute(
        select(User).where(User.email == req.email.lower().strip())
    ).scalars().first()

    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )

    merchant = db.get(Merchant, user.merchant_id)
    merchant_name = merchant.name if merchant else "Demo Merchant Inc."

    token = generate_session_token(user.id)
    _set_session_cookie(request, response, token)

    # Security: Token is NEVER returned in the JSON response payload.
    # The browser relies exclusively on the HTTP-only cookie.
    return {
        "status": "success",
        "message": "Authenticated successfully",
        "user": {
            "id": user.id,
            "merchant_id": user.merchant_id,
            "merchant_name": merchant_name,
            "email": user.email,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
    }


@router.post("/auth/logout")
def logout(response: Response) -> Dict[str, Any]:
    """Invalidate authenticated session by clearing HTTP-only cookie."""
    response.delete_cookie(key=SESSION_COOKIE_NAME)
    return {"status": "success", "message": "Logged out successfully"}


def get_current_active_user(request: Request, db: Session = Depends(get_db)) -> User:
    """FastAPI dependency to enforce authentication and retrieve current active user."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "").strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    user_id = verify_session_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )

    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return user


def get_optional_current_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """Retrieve current user if authenticated session cookie or header is present, else None."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "").strip()
    if not token:
        return None

    user_id = verify_session_token(token)
    if not user_id:
        return None

    user = db.get(User, user_id)
    if not user or not user.is_active:
        return None

    return user


@router.get("/auth/me")
def get_current_user(user: User = Depends(get_current_active_user), db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Retrieve authenticated user details from session cookie or Authorization header."""
    merchant = db.get(Merchant, user.merchant_id)
    merchant_name = merchant.name if merchant else "Demo Merchant Inc."

    return {
        "authenticated": True,
        "user": {
            "id": user.id,
            "merchant_id": user.merchant_id,
            "merchant_name": merchant_name,
            "email": user.email,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
    }
