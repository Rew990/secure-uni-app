"""Admin user management, and proof that every seeded student can log in."""
import pytest

from app.seed import STUDENT_LOGINS


def login(client, username, password):
    return client.post("/auth/login", json={"username": username, "password": password})


def auth(client, username, password):
    r = login(client, username, password)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_all_25_students_have_a_login():
    assert len(STUDENT_LOGINS) == 25
    passwords = [pw for _, pw in STUDENT_LOGINS.values()]
    assert len(set(passwords)) == 25          # nobody shares a password


@pytest.mark.parametrize("number,login_details", STUDENT_LOGINS.items(), ids=list(STUDENT_LOGINS))
def test_every_student_logs_in_and_sees_own_record(client, number, login_details):
    username, password = login_details
    h = auth(client, username, password)
    r = client.get("/students/me", headers=h)
    assert r.status_code == 200
    assert r.json()["student_number"] == number


def test_student_cannot_use_another_students_password(client):
    _, other_password = STUDENT_LOGINS["S1002"]
    assert login(client, "ahmed.hassan", other_password).status_code == 401


@pytest.mark.parametrize("user", ["instructor", "student"])
@pytest.mark.parametrize("method,path", [
    ("POST",   "/users"),
    ("PATCH",  "/users/1"),
])
def test_only_admin_manages_users(client, headers, user, method, path):
    body = {"username": "hacker", "password": "Hacker@12345", "role": "admin"}
    r = client.request(method, path, json=body, headers=headers[user])
    assert r.status_code == 403


def test_admin_creates_student_account(client, headers):
    r = client.post("/users", headers=headers["admin"], json={
        "username": "sara.second", "password": "Sara@12345", "role": "student", "student_number": "S1002"})
    assert r.status_code == 201
    h = auth(client, "sara.second", "Sara@12345")
    assert client.get("/students/me", headers=h).json()["student_number"] == "S1002"


@pytest.mark.parametrize("body,expected", [
    ({"role": "student"}, 400),                                   # student without a student number
    ({"role": "student", "student_number": "S0000"}, 404),        # student number that doesn't exist
    ({"role": "instructor", "student_number": "S1003"}, 400),     # only students have one
    ({"role": "student", "student_number": "S1003", "username": "admin"}, 409),  # name taken
])
def test_create_user_rejects_bad_input(client, headers, body, expected):
    full = {"username": "new.user", "password": "Passw0rd!x", **body}
    assert client.post("/users", json=full, headers=headers["admin"]).status_code == expected


def test_admin_resets_password(client, headers):
    created = client.post("/users", headers=headers["admin"], json={
        "username": "reset.me", "password": "OldPass@123", "role": "instructor"}).json()
    r = client.patch(f"/users/{created['id']}", json={"password": "NewPass@123"}, headers=headers["admin"])
    assert r.status_code == 200
    assert login(client, "reset.me", "OldPass@123").status_code == 401
    assert login(client, "reset.me", "NewPass@123").status_code == 200


def test_role_change_applies_to_the_next_request(client, headers):
    created = client.post("/users", headers=headers["admin"], json={
        "username": "promote.me", "password": "Promote@123", "role": "instructor"}).json()
    h = auth(client, "promote.me", "Promote@123")
    assert client.get("/users", headers=h).status_code == 403

    r = client.patch(f"/users/{created['id']}", json={"role": "admin"}, headers=headers["admin"])
    assert r.status_code == 200 and r.json()["role"] == "admin"
    # same token as before: require_role reads the role from the database, not the token
    assert client.get("/users", headers=h).status_code == 200


def test_changing_role_to_student_needs_student_number(client, headers):
    created = client.post("/users", headers=headers["admin"], json={
        "username": "to.student", "password": "ToStudent@1", "role": "instructor"}).json()
    url = f"/users/{created['id']}"
    assert client.patch(url, json={"role": "student"}, headers=headers["admin"]).status_code == 400
    r = client.patch(url, json={"role": "student", "student_number": "S1004"}, headers=headers["admin"])
    assert r.status_code == 200 and r.json()["student_id"] is not None


def test_admin_cannot_demote_self(client, headers):
    me = client.get("/auth/me", headers=headers["admin"]).json()
    r = client.patch(f"/users/{me['id']}", json={"role": "student", "student_number": "S1001"},
                     headers=headers["admin"])
    assert r.status_code == 400


def test_user_routes_cannot_change_grades(client, headers):
    """Separation of duties: the admin still can't change a GPA, even through /users."""
    before = client.get("/students/1", headers=headers["admin"]).json()["gpa"]
    client.patch("/users/1", json={"gpa": 0.0}, headers=headers["admin"])   # unknown field, ignored
    assert client.patch("/students/1/gpa", json={"gpa": 0.0}, headers=headers["admin"]).status_code == 403
    assert client.get("/students/1", headers=headers["admin"]).json()["gpa"] == before
