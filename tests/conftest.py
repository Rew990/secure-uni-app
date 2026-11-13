"""Test setup: a throwaway SQLite database (test.db), deleted after the run."""
import os

import pytest

os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["SEED_DEMO_USERS"] = "true"
os.environ["JWT_SECRET"] = "test-secret-test-secret-test-secret-1234"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

PASSWORDS = {"admin": "Admin@12345", "instructor": "Instructor@12345", "student": "Student@12345"}


@pytest.fixture(scope="session")
def client():
    if os.path.exists("test.db"):
        os.remove("test.db")
    with TestClient(app) as c:
        yield c
    os.remove("test.db")


@pytest.fixture(scope="session")
def headers(client):
    out = {}
    for user, pw in PASSWORDS.items():
        r = client.post("/auth/login", json={"username": user, "password": pw})
        assert r.status_code == 200, r.text
        out[user] = {"Authorization": f"Bearer {r.json()['access_token']}"}
    return out
