"""Forgot password : reset with the authenticator (TOTP) code."""
from urllib.parse import parse_qs, urlparse

import pyotp

from app.seed import STUDENT_LOGINS

# A separate account, so the seeded students' logins stay untouched for test_users.py
USERNAME, OLD_PASSWORD = "forgot.student", "Forgot@Pass1"
NEW_PASSWORD = "Forgot@NewPass9"


def login(client, username, password, code=None):
    body = {"username": username, "password": password}
    if code:
        body["totp_code"] = code
    return client.post("/auth/login", json=body)


def reset(client, username, code, new_password=NEW_PASSWORD):
    return client.post("/auth/reset-password",
                       json={"username": username, "totp_code": code, "new_password": new_password})


def turn_on_mfa(client, username, password) -> pyotp.TOTP:
    """What the student does in the app: set up MFA and confirm the first code."""
    token = login(client, username, password).json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    uri = client.post("/auth/mfa/setup", headers=h).json()["provisioning_uri"]
    totp = pyotp.TOTP(parse_qs(urlparse(uri).query)["secret"][0])   # what the authenticator app stores
    assert client.post("/auth/mfa/verify", json={"code": totp.now()}, headers=h).status_code == 200
    return totp


def test_reset_with_authenticator_code(client, headers):
    r = client.post("/users", headers=headers["admin"], json={
        "username": USERNAME, "password": OLD_PASSWORD, "role": "student", "student_number": "S1009"})
    assert r.status_code == 201
    totp = turn_on_mfa(client, USERNAME, OLD_PASSWORD)

    assert reset(client, USERNAME, "000000").status_code == 401           # wrong code
    assert reset(client, USERNAME, totp.now()).status_code == 204         # right code

    assert login(client, USERNAME, OLD_PASSWORD, totp.now()).status_code == 401   # old password gone
    assert login(client, USERNAME, NEW_PASSWORD, totp.now()).status_code == 200


def test_no_reset_without_mfa(client):
    # MFA not turned on: the student has to ask the admin instead
    username, _ = STUDENT_LOGINS["S1010"]
    assert reset(client, username, "123456").status_code == 401


def test_same_error_for_unknown_user(client):
    r = reset(client, "nobody.here", "123456")
    assert r.status_code == 401 and r.json()["detail"] == "Password reset failed"


def test_new_password_must_be_8_chars(client):
    assert reset(client, USERNAME, "123456", new_password="short").status_code == 422


def test_reset_is_rate_limited(client):
    # 5 tries a minute, then 429: stops someone guessing 6-digit codes
    codes = [reset(client, "nobody.here", "123456").status_code for _ in range(6)]
    assert codes == [401] * 5 + [429]
