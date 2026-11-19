"""TOTP multi-factor authentication (owner: Authentication & MFA).

Interface the rest of the app relies on. Implement with PyOTP so codes work
with Microsoft Authenticator. Login already calls `verify_totp` for any user
whose `mfa_enabled` is True.

TODO(auth):
  - store the secret encrypted (app.security.crypto.encrypt_field)
  - add /auth/mfa/setup and /auth/mfa/verify routes in app/routers/auth.py
  - rate limit login + MFA with SlowApi (see app/main.py)
"""

import pyotp


def generate_secret() -> str:
    return pyotp.random_base32()


def provisioning_uri(secret: str, username: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=username, issuer_name="SecureUni")


def verify_totp(secret: str, code: str) -> bool:
    return pyotp.TOTP(secret).verify(code, valid_window=1)

