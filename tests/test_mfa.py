"""Part 3 tests: TOTP MFA setup, verify, login, and rate limiting."""
from urllib.parse import parse_qs, urlparse

import pyotp
import pytest

from app.database import new_session
from app.limiter import limiter
from app.models import User
from app.roles import Role
from app.security.passwords import hash_password

USERNAME = "mfa_tester"
PASSWORD = "Mfa@12345"


@pytest.fixture(autouse=True)
def reset_rate_limit():
    """Start every test with a fresh 5-per-minute counter."""
    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture
def mfa_user(client):
    """A separate user, so the demo logins used by other tests never get MFA."""
    db = new_session()
    try:
        user = db.query(User).filter_by(username=USERNAME).first()
        if user is None:
            db.add(User(username=USERNAME, password_hash=hash_password(PASSWORD),
                        role=Role.INSTRUCTOR))
        else:
            user.mfa_enabled = False
            user.mfa_secret_enc = None
        db.commit()
    finally:
        db.close()


def login(client, code=None, password=PASSWORD):
    body = {"username": USERNAME, "password": password}
    if code:
        body["totp_code"] = code
    return client.post("/auth/login", json=body)


def test_setup_needs_login(client):
    assert client.post("/auth/mfa/setup").status_code == 401


def test_mfa_flow(client, mfa_user):
    token = login(client).json()["access_token"]
    auth = {"Authorization": f"Bearer {token}"}

    uri = client.post("/auth/mfa/setup", headers=auth).json()["provisioning_uri"]
    secret = parse_qs(urlparse(uri).query)["secret"][0]

    assert client.post("/auth/mfa/verify", headers=auth, json={"code": "000000"}).status_code == 401
    r = client.post("/auth/mfa/verify", headers=auth, json={"code": pyotp.TOTP(secret).now()})
    assert r.status_code == 200 and r.json()["mfa_enabled"] is True

    assert login(client).json()["detail"] == "MFA code required"
    assert login(client, "000000").json()["detail"] == "Invalid MFA code"
    assert login(client, pyotp.TOTP(secret).now()).status_code == 200


def test_secret_is_stored_encrypted(client, mfa_user):
    token = login(client).json()["access_token"]
    uri = client.post("/auth/mfa/setup",
                      headers={"Authorization": f"Bearer {token}"}).json()["provisioning_uri"]
    secret = parse_qs(urlparse(uri).query)["secret"][0]

    db = new_session()
    try:
        stored = db.query(User).filter_by(username=USERNAME).one().mfa_secret_enc
    finally:
        db.close()
    assert stored and secret not in stored


def test_login_is_rate_limited(client, mfa_user):
    for _ in range(5):
        assert login(client, password="wrong").status_code == 401
    assert login(client, password="wrong").status_code == 429
