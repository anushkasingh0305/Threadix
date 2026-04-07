import os
import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("CLOUDINARY_CLOUD_NAME", "test")
os.environ.setdefault("CLOUDINARY_API_KEY", "test")
os.environ.setdefault("CLOUDINARY_API_SECRET", "test")

from unittest.mock import AsyncMock, patch, MagicMock
from app.core.dependencies import CurrentUser
from app.services.thread_service import update_thread, delete_thread
from app.utils.exceptions import ForbiddenError, NotFoundError


def _make_thread(user_id=1, is_deleted=False):
    t = MagicMock()
    t.id = 10
    t.user_id = user_id
    t.is_deleted = is_deleted
    return t


def _user(id, role):
    return CurrentUser(id=id, username="u", avatar_url=None, role=role)


# ─── update_thread permissions ────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.services.thread_service.invalidate_thread_cache", new_callable=AsyncMock)
@patch("app.services.thread_service.ThreadRepository")
async def test_owner_can_edit(mock_repo, mock_cache):
    mock_repo.get_by_id = AsyncMock(return_value=_make_thread(user_id=1))
    mock_repo.update = AsyncMock(return_value=_make_thread())
    db = AsyncMock()
    from app.db.schemas import ThreadUpdate
    await update_thread(db, 10, _user(1, "member"), ThreadUpdate(title="new"))


@pytest.mark.asyncio
@patch("app.services.thread_service.invalidate_thread_cache", new_callable=AsyncMock)
@patch("app.services.thread_service.ThreadRepository")
async def test_admin_can_edit_others(mock_repo, mock_cache):
    mock_repo.get_by_id = AsyncMock(return_value=_make_thread(user_id=1))
    mock_repo.update = AsyncMock(return_value=_make_thread())
    db = AsyncMock()
    from app.db.schemas import ThreadUpdate
    await update_thread(db, 10, _user(99, "admin"), ThreadUpdate(title="new"))


@pytest.mark.asyncio
@patch("app.services.thread_service.ThreadRepository")
async def test_moderator_cannot_edit_others(mock_repo):
    mock_repo.get_by_id = AsyncMock(return_value=_make_thread(user_id=1))
    db = AsyncMock()
    from app.db.schemas import ThreadUpdate
    with pytest.raises(ForbiddenError):
        await update_thread(db, 10, _user(99, "moderator"), ThreadUpdate(title="new"))


@pytest.mark.asyncio
@patch("app.services.thread_service.ThreadRepository")
async def test_member_cannot_edit_others(mock_repo):
    mock_repo.get_by_id = AsyncMock(return_value=_make_thread(user_id=1))
    db = AsyncMock()
    from app.db.schemas import ThreadUpdate
    with pytest.raises(ForbiddenError):
        await update_thread(db, 10, _user(99, "member"), ThreadUpdate(title="new"))


@pytest.mark.asyncio
@patch("app.services.thread_service.ThreadRepository")
async def test_edit_deleted_thread_404(mock_repo):
    mock_repo.get_by_id = AsyncMock(return_value=_make_thread(is_deleted=True))
    db = AsyncMock()
    from app.db.schemas import ThreadUpdate
    with pytest.raises(NotFoundError):
        await update_thread(db, 10, _user(1, "admin"), ThreadUpdate(title="xxx"))


# ─── delete_thread permissions ────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.services.thread_service.invalidate_thread_cache", new_callable=AsyncMock)
@patch("app.services.thread_service.ThreadRepository")
async def test_owner_can_delete(mock_repo, mock_cache):
    mock_repo.get_by_id = AsyncMock(return_value=_make_thread(user_id=1))
    mock_repo.soft_delete = AsyncMock()
    db = AsyncMock()
    await delete_thread(db, 10, _user(1, "member"))


@pytest.mark.asyncio
@patch("app.services.thread_service.invalidate_thread_cache", new_callable=AsyncMock)
@patch("app.services.thread_service.ThreadRepository")
async def test_moderator_can_delete_others(mock_repo, mock_cache):
    mock_repo.get_by_id = AsyncMock(return_value=_make_thread(user_id=1))
    mock_repo.soft_delete = AsyncMock()
    db = AsyncMock()
    await delete_thread(db, 10, _user(99, "moderator"))


@pytest.mark.asyncio
@patch("app.services.thread_service.invalidate_thread_cache", new_callable=AsyncMock)
@patch("app.services.thread_service.ThreadRepository")
async def test_admin_can_delete_others(mock_repo, mock_cache):
    mock_repo.get_by_id = AsyncMock(return_value=_make_thread(user_id=1))
    mock_repo.soft_delete = AsyncMock()
    db = AsyncMock()
    await delete_thread(db, 10, _user(99, "admin"))


@pytest.mark.asyncio
@patch("app.services.thread_service.ThreadRepository")
async def test_member_cannot_delete_others(mock_repo):
    mock_repo.get_by_id = AsyncMock(return_value=_make_thread(user_id=1))
    db = AsyncMock()
    with pytest.raises(ForbiddenError):
        await delete_thread(db, 10, _user(99, "member"))
