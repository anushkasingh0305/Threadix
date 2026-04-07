import os
import hashlib
import pytest

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests")
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

from unittest.mock import AsyncMock, patch, MagicMock
from app.services.auth_service import register_user, login_user, refresh_tokens, logout_user
from app.db.models import User, UserRole
from app.core.security import create_refresh_token


def _make_user(id=1, email="a@b.com", username="alice",
               password_hash=None, role=UserRole.member,
               is_deleted=False, avatar_url=None):
    from app.core.hashing import hash_password
    u = MagicMock(spec=User)
    u.id = id
    u.email = email
    u.username = username
    u.password_hash = password_hash or hash_password("Secret123")
    u.role = role
    u.is_deleted = is_deleted
    u.avatar_url = avatar_url
    return u


@pytest.mark.asyncio
@patch("app.services.auth_service.UserRepository")
async def test_register_duplicate_email(mock_repo):
    mock_repo.get_by_email = AsyncMock(return_value=_make_user())
    db = AsyncMock()
    from app.db.schemas import UserRegister
    data = UserRegister(email="a@b.com", password="Secret123", username="bob")
    with pytest.raises(Exception, match="Email already exists"):
        await register_user(db, data)


@pytest.mark.asyncio
@patch("app.services.auth_service.UserRepository")
async def test_register_duplicate_username(mock_repo):
    mock_repo.get_by_email = AsyncMock(return_value=None)
    mock_repo.get_by_username = AsyncMock(return_value=_make_user())
    db = AsyncMock()
    from app.db.schemas import UserRegister
    data = UserRegister(email="new@b.com", password="Secret123", username="alice")
    with pytest.raises(Exception, match="Username already taken"):
        await register_user(db, data)


@pytest.mark.asyncio
@patch("app.services.auth_service.set_key", new_callable=AsyncMock)
@patch("app.services.auth_service.UserRepository")
async def test_login_success(mock_repo, mock_set_key):
    user = _make_user()
    mock_repo.get_by_email = AsyncMock(return_value=user)
    db = AsyncMock()
    from app.db.schemas import UserLogin
    data = UserLogin(email="a@b.com", password="Secret123")
    access, refresh = await login_user(db, data)
    assert isinstance(access, str)
    assert isinstance(refresh, str)
    mock_set_key.assert_called_once()


@pytest.mark.asyncio
@patch("app.services.auth_service.UserRepository")
async def test_login_wrong_password(mock_repo):
    user = _make_user()
    mock_repo.get_by_email = AsyncMock(return_value=user)
    db = AsyncMock()
    from app.db.schemas import UserLogin
    data = UserLogin(email="a@b.com", password="WrongPass")
    with pytest.raises(Exception, match="Invalid password"):
        await login_user(db, data)


@pytest.mark.asyncio
@patch("app.services.auth_service.UserRepository")
async def test_login_deleted_user(mock_repo):
    user = _make_user(is_deleted=True)
    mock_repo.get_by_email = AsyncMock(return_value=user)
    db = AsyncMock()
    from app.db.schemas import UserLogin
    data = UserLogin(email="a@b.com", password="Secret123")
    with pytest.raises(Exception, match="User not found"):
        await login_user(db, data)


@pytest.mark.asyncio
@patch("app.services.auth_service.set_key", new_callable=AsyncMock)
@patch("app.services.auth_service.delete_key", new_callable=AsyncMock)
@patch("app.services.auth_service.get_key", new_callable=AsyncMock)
@patch("app.services.auth_service.UserRepository")
async def test_refresh_tokens_success(mock_repo, mock_get, mock_del, mock_set):
    token = create_refresh_token({"sub": "1"})
    hashed = hashlib.sha256(token.encode()).hexdigest()
    mock_get.return_value = hashed
    user = _make_user()
    mock_repo.get_by_id = AsyncMock(return_value=user)
    db = AsyncMock()
    access, new_refresh = await refresh_tokens(token, db=db)
    assert isinstance(access, str)
    assert isinstance(new_refresh, str)
    mock_del.assert_called_once()
    mock_set.assert_called_once()


@pytest.mark.asyncio
@patch("app.services.auth_service.get_key", new_callable=AsyncMock)
async def test_refresh_tokens_reuse_rejected(mock_get):
    token = create_refresh_token({"sub": "1"})
    mock_get.return_value = "wrong-hash"
    with pytest.raises(Exception, match="Session expired or token reuse"):
        await refresh_tokens(token)


@pytest.mark.asyncio
@patch("app.services.auth_service.delete_key", new_callable=AsyncMock)
async def test_logout_deletes_key(mock_del):
    await logout_user("42")
    mock_del.assert_called_once_with("refresh:42")
