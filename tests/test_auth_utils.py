# tests/test_auth_utils.py
import os
import sys
from datetime import timedelta, datetime, timezone

# make project importable
ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from jose import jwt

from auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    SECRET_KEY,
    ALGORITHM,
)


def test_password_hash_and_verify_roundtrip():
    # Arrange
    plain = "MySecureP@ssw0rd"

    # Act
    hashed = get_password_hash(plain)

    # Assert
    assert hashed != plain  # definitely not storing plaintext
    assert verify_password(plain, hashed) is True


def test_verify_password_wrong_password():
    plain = "correct-horse-battery-staple"
    other = "wrong-password"

    hashed = get_password_hash(plain)

    assert verify_password(other, hashed) is False


def test_create_access_token_contains_sub_and_exp():
    # Arrange
    data = {"sub": "testuser"}
    delta = timedelta(minutes=5)

    # Act
    token = create_access_token(data=data, expires_delta=delta)

    # Assert basic structure
    assert isinstance(token, str)
    decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

    assert decoded["sub"] == "testuser"
    assert "exp" in decoded

    # exp should be in the future (within ~10 minutes)
    exp = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)
    now = datetime.now(timezone.utc)
    assert now < exp < now + timedelta(minutes=10)
