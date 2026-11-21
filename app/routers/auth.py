"""Login (owner: Authentication & MFA; token issuing shared with RBAC)."""
import io

import qrcode
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_session
from app.limiter import limiter
from app.models import User
from app.schemas import LoginRequest, Token, UserOut, PasswordReset
from app.security import mfa
from app.security.crypto import decrypt_field, encrypt_field
from app.security.passwords import hash_password, verify_password
from app.security.rbac import get_current_user
from app.security.tokens import create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


class MfaCode(BaseModel):
    code: str


@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
def login(request: Request, body: LoginRequest, db: Session = Depends(get_session)) -> Token:
    user = db.scalar(select(User).where(User.username == body.username))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password")

    if user.mfa_enabled:
        if not body.totp_code:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "MFA code required")
        secret = decrypt_field(user.mfa_secret_enc)
        if not mfa.verify_totp(secret, body.totp_code):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid MFA code")

    return Token(access_token=create_access_token(user.id, user.role))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user


def _start_mfa_setup(current: User, db: Session) -> str:
    """Make a new secret, store it encrypted, keep MFA off, return the otpauth:// link."""
    user = db.get(User, current.id)
    if user.mfa_enabled:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "MFA is already enabled")
    secret = mfa.generate_secret()
    user.mfa_secret_enc = encrypt_field(secret)
    user.mfa_enabled = False
    db.commit()
    return mfa.provisioning_uri(secret, user.username)


@router.post("/mfa/setup")
def mfa_setup(
    current: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> dict:
    return {"provisioning_uri": _start_mfa_setup(current, db)}


@router.post(
    "/mfa/setup/qr",
    response_class=Response,
    responses={200: {"content": {"image/png": {}}, "description": "QR code to scan"}},
)
def mfa_setup_qr(
    current: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> Response:
    uri = _start_mfa_setup(current, db)
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return Response(buf.getvalue(), media_type="image/png")


@router.post("/mfa/verify")
@limiter.limit("5/minute")
def mfa_verify(
    request: Request,
    body: MfaCode,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> dict:
    user = db.get(User, current.id)
    if not user.mfa_secret_enc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Call /auth/mfa/setup first")
    secret = decrypt_field(user.mfa_secret_enc)
    if not mfa.verify_totp(secret, body.code):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid MFA code")
    user.mfa_enabled = True
    db.commit()
    return {"mfa_enabled": True}


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("5/minute")
def reset_password(request: Request, body: PasswordReset, db: Session = Depends(get_session)) -> None:
    failed = HTTPException(status.HTTP_401_UNAUTHORIZED, "Password reset failed")
    user = db.scalar(select(User).where(User.username == body.username))
    if user is None or not user.mfa_enabled or not user.mfa_secret_enc:
        raise failed
    if not mfa.verify_totp(decrypt_field(user.mfa_secret_enc), body.totp_code):
        raise failed
    user.password_hash = hash_password(body.new_password)
    db.commit()
