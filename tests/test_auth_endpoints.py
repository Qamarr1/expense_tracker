import os
import sys
from datetime import timedelta
from sqlmodel import Session, select

from main import app, get_session  # noqa: E402
from models import User  # noqa: E402
from auth import create_access_token  # noqa: E402


# ---------- core auth tests ----------

def test_register_and_login_success(auth_helpers):
    register_user = auth_helpers["register_user"]
    login_user = auth_helpers["login_user"]
    # Arrange
    username = "alice"
    password = "SuperSecret123!"

    # Act: register
    r_reg = register_user(username, password)
    assert r_reg.status_code in (200, 201)

    # Act: login
    r_login = login_user(username, password)

    # Assert
    assert r_login.status_code == 200
    data = r_login.json()
    assert "access_token" in data
    assert data["access_token"]
    assert data.get("token_type", "").lower() == "bearer"


def test_register_duplicate_username_rejected(auth_helpers):
    register_user = auth_helpers["register_user"]
    username = "bob"
    password = "Password123!"

    r1 = register_user(username, password)
    assert r1.status_code in (200, 201)

    r2 = register_user(username, password)
    # API uses 400 for "Username already registered"
    assert r2.status_code == 400
    body = r2.json()
    assert "detail" in body


def test_login_unknown_user_unauthorized(auth_helpers):
    login_user = auth_helpers["login_user"]
    r_login = login_user("does_not_exist", "whatever123")
    # your implementation: 400 Incorrect username or password
    assert r_login.status_code == 400
    body = r_login.json()
    assert "detail" in body


def test_login_wrong_password_unauthorized(auth_helpers):
    register_user = auth_helpers["register_user"]
    login_user = auth_helpers["login_user"]
    username = "charlie"
    correct = "Correct123!"
    wrong = "Wrong123!"

    # Ensure user exists
    r_reg = register_user(username, correct)
    assert r_reg.status_code in (200, 201, 400)

    # Try wrong password
    r_login = login_user(username, wrong)
    assert r_login.status_code == 400
    body = r_login.json()
    assert "detail" in body


# ---------- 1) Input validation edge cases ----------

def test_login_empty_username_or_password(client):
    # empty username
    r1 = client.post(
        "/auth/login",
        json={"username": "", "password": "SomePass123"},
    )
    # could be 422 (Pydantic) or 400 (manual)
    assert r1.status_code in (400, 422)
    assert "detail" in r1.json()

    # empty password
    r2 = client.post(
        "/auth/login",
        json={"username": "someone", "password": ""},
    )
    assert r2.status_code in (400, 422)
    assert "detail" in r2.json()


def test_login_very_long_username_and_password(client):
    long_username = "u" * 300
    long_password = "p" * 300

    # We don't care exactly which error code, but it must not be 500
    r = client.post(
        "/auth/login",
        json={"username": long_username, "password": long_password},
    )
    assert r.status_code in (400, 401, 422)
    assert "detail" in r.json()


# ---------- 2) Account state / existence edge cases ----------

def test_login_deleted_user_behaves_like_unknown(auth_helpers, client):
    register_user = auth_helpers["register_user"]
    login_user = auth_helpers["login_user"]
    username = "to_delete"
    password = "DeleteMe123!"

    # create user
    r_reg = register_user(username, password)
    assert r_reg.status_code in (200, 201, 400)

    # delete directly from test DB
    for session in auth_helpers["session_factory"]():
        user = session.exec(
            select(User).where(User.username == username)
        ).first()
        if user:
            session.delete(user)
            session.commit()

    # login now should behave like "unknown user"
    r_login = login_user(username, password)
    assert r_login.status_code == 400
    body = r_login.json()
    assert "detail" in body


def test_username_is_case_sensitive(auth_helpers):
    register_user = auth_helpers["register_user"]
    login_user = auth_helpers["login_user"]
    # Register capitalized
    r_reg = register_user("UserCase", "CasePass123!")
    assert r_reg.status_code in (200, 201, 400)

    # Login with different case → should fail
    r_login = login_user("usercase", "CasePass123!")
    assert r_login.status_code == 400
    body = r_login.json()
    assert "detail" in body


# ---------- 3) Password change flow (already partially covered) ----------

def test_change_password_requires_auth(client):
    r = client.post(
        "/auth/change-password",
        json={"current_password": "x", "new_password": "y"},
    )
    assert r.status_code in (401, 403)


def test_change_password_success_new_login_works(auth_helpers, client):
    get_token = auth_helpers["get_token"]
    login_user = auth_helpers["login_user"]
    username = "erin"
    old_pw = "OldPass123!"
    new_pw = "NewPass123!"

    # register + login
    token = get_token(username, old_pw)

    # change password
    r_change = client.post(
        "/auth/change-password",
        headers=auth_helpers["auth_headers"](token),
        json={"current_password": old_pw, "new_password": new_pw},
    )
    assert r_change.status_code == 200

    # old password should no longer work
    r_old = login_user(username, old_pw)
    assert r_old.status_code == 400

    # new password should work
    r_new = login_user(username, new_pw)
    assert r_new.status_code == 200
    assert "access_token" in r_new.json()


def test_change_password_wrong_current_rejected(auth_helpers, client):
    get_token = auth_helpers["get_token"]
    username = "frank"
    real_pw = "RealPass123!"
    token = get_token(username, real_pw)

    r_change = client.post(
        "/auth/change-password",
        headers=auth_helpers["auth_headers"](token),
        json={"current_password": "WrongPass!", "new_password": "DoesntMatter123"},
    )
    assert r_change.status_code == 400
    body = r_change.json()
    assert "detail" in body


# ---------- 4) /auth/me (current user) ----------

def test_me_requires_auth(client):
    r = client.get("/auth/me")
    assert r.status_code in (401, 403)


def test_me_returns_current_user(auth_helpers, client):
    get_token = auth_helpers["get_token"]
    username = "dora"
    password = "Map12345!"

    token = get_token(username, password)

    r = client.get("/auth/me", headers=auth_helpers["auth_headers"](token))
    assert r.status_code == 200
    data = r.json()
    assert data["username"] == username


# ---------- 5) Change username flow ----------

def test_change_username_success_and_login_with_new(auth_helpers, client):
    get_token = auth_helpers["get_token"]
    login_user = auth_helpers["login_user"]
    old_username = "grace"
    new_username = "grace_new"
    password = "SomePass123!"

    token = get_token(old_username, password)

    # change username -> backend also returns a new token
    r_change = client.post(
        "/auth/change-username",
        headers=auth_helpers["auth_headers"](token),
        json={"new_username": new_username},
    )
    assert r_change.status_code == 200
    data_change = r_change.json()
    assert "access_token" in data_change
    new_token = data_change["access_token"]

    # /auth/me with NEW token should show the new username
    r_me = client.get("/auth/me", headers=auth_helpers["auth_headers"](new_token))
    assert r_me.status_code == 200
    data_me = r_me.json()
    assert data_me["username"] == new_username

    # old username should no longer log in
    r_old_login = login_user(old_username, password)
    assert r_old_login.status_code == 400

    # new username should log in
    r_new_login = login_user(new_username, password)
    assert r_new_login.status_code == 200
    assert "access_token" in r_new_login.json()


def test_change_username_duplicate_rejected(auth_helpers, client):
    register_user = auth_helpers["register_user"]
    get_token = auth_helpers["get_token"]
    # user1
    r1 = register_user("henry", "Pass123!")
    assert r1.status_code in (200, 201, 400)

    # user2
    r2 = register_user("irene", "Pass456!")
    assert r2.status_code in (200, 201, 400)

    token_user2 = get_token("irene", "Pass456!")

    # user2 tries to rename to "henry" → should fail
    r_change = client.post(
        "/auth/change-username",
        headers=auth_helpers["auth_headers"](token_user2),
        json={"new_username": "henry"},
    )
    assert r_change.status_code == 400
    body = r_change.json()
    assert "detail" in body


# ---------- 6) Token / JWT robustness ----------

def test_me_with_tampered_token_unauthorized(auth_helpers, client):
    get_token = auth_helpers["get_token"]
    username = "tamperuser"
    password = "TamperPass123!"
    token = get_token(username, password)

    # flip the last character so signature is invalid
    if len(token) > 10:
        tampered = token[:-1] + ("x" if token[-1] != "x" else "y")
    else:
        tampered = token + "x"

    r = client.get("/auth/me", headers=auth_helpers["auth_headers"](tampered))
    assert r.status_code in (401, 403)


def test_me_with_expired_token_unauthorized(auth_helpers, client):
    register_user = auth_helpers["register_user"]
    username = "expireduser"
    password = "Expire123!"
    # ensure user exists
    register_user(username, password)

    # create token already expired 5 minutes ago
    expired_token = create_access_token(
        {"sub": username},
        expires_delta=timedelta(minutes=-5),
    )

    r = client.get("/auth/me", headers=auth_helpers["auth_headers"](expired_token))
    assert r.status_code in (401, 403)


def test_me_with_token_for_deleted_user_unauthorized(auth_helpers, client):
    get_token = auth_helpers["get_token"]
    auth_headers = auth_helpers["auth_headers"]
    username = "zombie"
    password = "Zombie123!"
    token = get_token(username, password)

    # delete user from DB
    for session in auth_helpers["session_factory"]():
        user = session.exec(
            select(User).where(User.username == username)
        ).first()
        if user:
            session.delete(user)
            session.commit()

    r = client.get("/auth/me", headers=auth_headers(token))
    assert r.status_code in (401, 403)
