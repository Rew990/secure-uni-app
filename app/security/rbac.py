"""Role-based access control (owner: Core app / RBAC).

`require_role(...)` returns 401 without a valid token and 403 when the
caller's role is not allowed. Every protected route must use it: with SQLite
there is no database-level permission layer behind it.
"""
from collections.abc import Callable, Iterator

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_session
from app.models import User
from app.roles import Role
from app.security.tokens import decode_access_token

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_session),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if creds is None:
        raise unauthorized
    try:
        payload = decode_access_token(creds.credentials)
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise unauthorized
    user = db.get(User, user_id)
    if user is None:
        raise unauthorized
    return user


def require_role(*allowed: Role) -> Callable[..., User]:
    """Dependency factory: `Depends(require_role(Role.ADMIN))`."""

    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden for your role")
        return user

    return checker


def get_db(user: User = Depends(get_current_user)) -> Iterator[Session]:
    """DB session for an authenticated caller (401 if there is no valid token)."""
    yield from get_session()
