import base64
import os

import pytest
from sqlalchemy import select

from app.config import get_settings
from app.database import new_session
from app.models import Student
from app.security.crypto import DecryptionError, decrypt_field, encrypt_field


@pytest.fixture
def other_key(monkeypatch):
    monkeypatch.setenv("FIELD_ENCRYPTION_KEY", base64.b64encode(os.urandom(32)).decode())
    get_settings.cache_clear()
    yield
    monkeypatch.undo()
    get_settings.cache_clear()


def test_round_trip():
    assert decrypt_field(encrypt_field("29801011234567")) == "29801011234567"


def test_round_trip_unicode():
    assert decrypt_field(encrypt_field("محمد خليل")) == "محمد خليل"


def test_ciphertext_hides_plaintext():
    token = encrypt_field("29801011234567")
    assert "29801011234567" not in token
    assert b"29801011234567" not in base64.b64decode(token)


def test_same_input_gives_different_ciphertext():
    assert encrypt_field("same") != encrypt_field("same")


def test_tampering_is_detected():
    blob = bytearray(base64.b64decode(encrypt_field("29801011234567")))
    blob[-1] ^= 0x01
    with pytest.raises(DecryptionError):
        decrypt_field(base64.b64encode(blob).decode())


def test_tampered_ciphertext_body_is_detected():
    blob = bytearray(base64.b64decode(encrypt_field("29801011234567")))
    blob[12] ^= 0x01
    with pytest.raises(DecryptionError):
        decrypt_field(base64.b64encode(blob).decode())


def test_wrong_aad_is_rejected():
    token = encrypt_field("secret", aad=b"students.national_id")
    assert decrypt_field(token, aad=b"students.national_id") == "secret"
    with pytest.raises(DecryptionError):
        decrypt_field(token, aad=b"users.mfa_secret")


def test_wrong_key_is_rejected(other_key):
    token = encrypt_field("secret")
    os.environ["FIELD_ENCRYPTION_KEY"] = base64.b64encode(os.urandom(32)).decode()
    get_settings.cache_clear()
    with pytest.raises(DecryptionError):
        decrypt_field(token)


@pytest.mark.parametrize("bad", ["not base64!!", "", base64.b64encode(b"short").decode()])
def test_garbage_input_is_rejected(bad):
    with pytest.raises(DecryptionError):
        decrypt_field(bad)


def test_missing_key_refuses_to_run(monkeypatch):
    monkeypatch.setenv("FIELD_ENCRYPTION_KEY", "")
    get_settings.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="FIELD_ENCRYPTION_KEY"):
            encrypt_field("x")
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()


def test_wrong_key_length_refuses_to_run(monkeypatch):
    monkeypatch.setenv("FIELD_ENCRYPTION_KEY", base64.b64encode(os.urandom(16)).decode())
    get_settings.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="32 bytes"):
            encrypt_field("x")
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()


def test_national_id_is_stored_encrypted(client, headers):
    body = dict(student_number="S8888", full_name="Crypto Test", birth_year=2003,
                gender="M", zip_code="11837", department="CS", gpa=3.5,
                national_id="30301011234567")
    r = client.post("/students", json=body, headers=headers["admin"])
    assert r.status_code == 201, r.text
    assert "national_id" not in r.json()

    with new_session() as db:
        row = db.scalar(select(Student).where(Student.student_number == "S8888"))
    assert row.national_id_enc is not None
    assert "30301011234567" not in row.national_id_enc
    assert decrypt_field(row.national_id_enc) == "30301011234567"
