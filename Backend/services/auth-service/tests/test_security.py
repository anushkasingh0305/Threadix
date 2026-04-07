import os
import jwt as pyjwt
import pytest

# Set env vars before importing app modules
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests")
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

from app.core.security import create_access_token, create_refresh_token, decode_token
from app.core.config import settings


def test_access_token_contains_claims():
    token = create_access_token({"sub": "42", "role": "member", "username": "alice"})
    payload = decode_token(token)
    assert payload["sub"] == "42"
    assert payload["role"] == "member"
    assert payload["username"] == "alice"
    assert "exp" in payload


def test_refresh_token_contains_sub():
    token = create_refresh_token({"sub": "42"})
    payload = decode_token(token)
    assert payload["sub"] == "42"
    assert "exp" in payload


def test_access_token_has_expiry():
    token = create_access_token({"sub": "1"})
    payload = pyjwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert "exp" in payload


def test_decode_invalid_token_raises():
    with pytest.raises(Exception):
        decode_token("not.a.valid.token")


def test_decode_wrong_secret_raises():
    token = pyjwt.encode({"sub": "1"}, "wrong-secret", algorithm="HS256")
    with pytest.raises(Exception):
        decode_token(token)
