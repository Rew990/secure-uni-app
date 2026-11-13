"""Login (owner: Authentication & MFA; token issuing shared with RBAC)."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_session
from app.models import User
from app.schemas import LoginRequest, Token, UserOut
from app.security import mfa
from app.security.passwords import verify_password
from app.security.rbac import get_current_user
from app.security.tokens import create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
def login(body: LoginRequest, db: Session = Depends(get_session)) -> Token:
    # TODO(auth): @limiter.limit("5/minute") once SlowApi is wired in main.py
    user = db.scalar(select(User).where(User.username == body.username))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password")

    if user.mfa_enabled:
        if not body.totp_code:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "MFA code required")
        # TODO(auth/encryption): decrypt user.mfa_secret_enc before verifying
        if not mfa.verify_totp(user.mfa_secret_enc or "", body.totp_code):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid MFA code")

    return Token(access_token=create_access_token(user.id, user.role))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user


# TODO(auth): POST /auth/mfa/setup  -> returns provisioning URI / QR code
# TODO(auth): POST /auth/mfa/verify -> confirms first code, sets mfa_enabled=True
