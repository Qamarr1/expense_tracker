import os
import sys
import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy.pool import StaticPool

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from main import app, get_session  # noqa: E402


test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
DBSession = Session


@pytest.fixture(scope="function")
def client():
    """Return a TestClient wired to a fresh in-memory database for each test."""
    SQLModel.metadata.drop_all(test_engine)
    SQLModel.metadata.create_all(test_engine)

    def override_get_session():
        with DBSession(test_engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_helpers(client):
    """
    Common auth utilities shared across test modules.
    Provides register/login helpers and a token helper.
    """
    override = client.app.dependency_overrides
    session_dep = override[get_session]

    def session_factory():
        """Yield a real Session from the overridden dependency."""
        # session_dep is a generator dependency; this makes it an explicit context manager
        cm = session_dep()
        try:
            session = next(cm)
            try:
                yield session
            finally:
                try:
                    next(cm)
                except StopIteration:
                    pass
        finally:
            if hasattr(cm, "close"):
                cm.close()

    def register_user(username: str, password: str):
        return client.post("/auth/register", json={"username": username, "password": password})

    def login_user(username: str, password: str):
        return client.post("/auth/login", json={"username": username, "password": password})

    def get_token(username: str, password: str) -> str:
        res_reg = register_user(username, password)
        assert res_reg.status_code in (200, 201, 400)
        res_login = login_user(username, password)
        assert res_login.status_code == 200
        data = res_login.json()
        assert "access_token" in data
        return data["access_token"]

    def auth_headers(token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}

    return {
        "register_user": register_user,
        "login_user": login_user,
        "get_token": get_token,
        "auth_headers": auth_headers,
        "session_factory": session_factory,
    }
