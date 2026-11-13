"""TOTP multi-factor authentication (owner: Authentication & MFA).

Interface the rest of the app relies on. Implement with PyOTP so codes work
with Microsoft Authenticator. Login already calls `verify_totp` for any user
whose `mfa_enabled` is True.

TODO(auth):
  - generate_secret(): pyotp.random_base32()
  - provisioning_uri(): pyotp.TOTP(secret).provisioning_uri(name=username, issuer_name="SecureUni")
  - verify_totp(): pyotp.TOTP(secret).verify(code, valid_window=1)
  - store the secret encrypted (app.security.crypto.encrypt_field)
  - add /auth/mfa/setup and /auth/mfa/verify routes in app/routers/auth.py
  - rate limit login + MFA with SlowApi (see app/main.py)
"""


def generate_secret() -> str:
    raise NotImplementedError("MFA: generate_secret")


def provisioning_uri(secret: str, username: str) -> str:
    raise NotImplementedError("MFA: provisioning_uri")


def verify_totp(secret: str, code: str) -> bool:
    raise NotImplementedError("MFA: verify_totp")
