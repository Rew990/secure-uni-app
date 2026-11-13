"""Proof that each role gets 200 where allowed and 403 where blocked."""
import pytest

NEW_STUDENT = dict(student_number="S9999", full_name="Test Student", birth_year=2004,
                   gender="F", zip_code="11533", department="IS", gpa=3.0)


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_wrong_password_rejected(client):
    r = client.post("/auth/login", json={"username": "admin", "password": "nope"})
    assert r.status_code == 401


def test_no_token_is_401(client):
    assert client.get("/students").status_code == 401


def test_bad_token_is_401(client):
    assert client.get("/students", headers={"Authorization": "Bearer junk"}).status_code == 401


@pytest.mark.parametrize("user,method,path,expected", [
    ("admin",   "GET", "/students",   200),
    ("instructor", "GET", "/students",   200),
    ("student",  "GET", "/students",   403),
    ("admin",   "GET", "/anonymized", 200),
    ("instructor", "GET", "/anonymized", 200),
    ("student",  "GET", "/anonymized", 200),
    ("admin",   "GET", "/users",      200),
    ("instructor", "GET", "/users",      403),
    ("student",  "GET", "/users",      403),
])
def test_read_matrix(client, headers, user, method, path, expected):
    assert client.request(method, path, headers=headers[user]).status_code == expected


@pytest.mark.parametrize("user,expected", [("instructor", 403), ("student", 403)])
def test_only_admin_changes_grades(client, headers, user, expected):
    r = client.patch("/students/1/gpa", json={"gpa": 4.0}, headers=headers[user])
    assert r.status_code == expected


def test_admin_changes_grade(client, headers):
    r = client.patch("/students/1/gpa", json={"gpa": 3.7}, headers=headers["admin"])
    assert r.status_code == 200 and r.json()["gpa"] == 3.7


@pytest.mark.parametrize("user,expected", [("admin", 201), ("instructor", 403), ("student", 403)])
def test_create_student(client, headers, user, expected):
    body = {**NEW_STUDENT, "student_number": f"S9{user[:3]}"}
    assert client.post("/students", json=body, headers=headers[user]).status_code == expected


def test_me_returns_role(client, headers):
    assert client.get("/auth/me", headers=headers["viewer"]).json()["role"] == "viewer"
