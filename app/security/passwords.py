"""Password hashing with Argon2id (owner: Authentication & MFA).

Working baseline so login and RBAC can be tested from day one.
TODO(auth): tune Argon2 parameters, add password policy checks.
"""
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

_ph = PasswordHasher()


def hash_password(plain: str) -> str:
    return _ph.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, plain)
    except (VerifyMismatchError, InvalidHashError):
        return False
