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
from app.services.comment_service import update_comment, delete_comment
from app.utils.exceptions import ForbiddenError, NotFoundError, ValidationError


def _make_comment(user_id=1, is_deleted=False, thread_id=5):
    c = MagicMock()
    c.id = 20
    c.user_id = user_id
    c.is_deleted = is_deleted
    c.thread_id = thread_id
    return c


def _user(id, role):
    return CurrentUser(id=id, username="u", avatar_url=None, role=role)


# ─── update_comment permissions ───────────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.services.comment_service.CommentRepository")
async def test_owner_can_edit_comment(mock_repo):
    mock_repo.get_by_id = AsyncMock(return_value=_make_comment(user_id=1))
    mock_repo.update_content = AsyncMock()
    db = AsyncMock()
    from app.db.schemas import CommentUpdate
    await update_comment(db, 20, _user(1, "member"), CommentUpdate(content="edited"))


@pytest.mark.asyncio
@patch("app.services.comment_service.CommentRepository")
async def test_admin_can_edit_others_comment(mock_repo):
    mock_repo.get_by_id = AsyncMock(return_value=_make_comment(user_id=1))
    mock_repo.update_content = AsyncMock()
    db = AsyncMock()
    from app.db.schemas import CommentUpdate
    await update_comment(db, 20, _user(99, "admin"), CommentUpdate(content="edited"))


@pytest.mark.asyncio
@patch("app.services.comment_service.CommentRepository")
async def test_moderator_cannot_edit_others_comment(mock_repo):
    mock_repo.get_by_id = AsyncMock(return_value=_make_comment(user_id=1))
    db = AsyncMock()
    from app.db.schemas import CommentUpdate
    with pytest.raises(ForbiddenError):
        await update_comment(db, 20, _user(99, "moderator"), CommentUpdate(content="x"))


@pytest.mark.asyncio
@patch("app.services.comment_service.CommentRepository")
async def test_member_cannot_edit_others_comment(mock_repo):
    mock_repo.get_by_id = AsyncMock(return_value=_make_comment(user_id=1))
    db = AsyncMock()
    from app.db.schemas import CommentUpdate
    with pytest.raises(ForbiddenError):
        await update_comment(db, 20, _user(99, "member"), CommentUpdate(content="x"))


@pytest.mark.asyncio
@patch("app.services.comment_service.CommentRepository")
async def test_cannot_edit_deleted_comment(mock_repo):
    mock_repo.get_by_id = AsyncMock(return_value=_make_comment(is_deleted=True))
    db = AsyncMock()
    from app.db.schemas import CommentUpdate
    with pytest.raises(ValidationError):
        await update_comment(db, 20, _user(1, "member"), CommentUpdate(content="x"))


@pytest.mark.asyncio
@patch("app.services.comment_service.CommentRepository")
async def test_edit_nonexistent_comment_404(mock_repo):
    mock_repo.get_by_id = AsyncMock(return_value=None)
    db = AsyncMock()
    from app.db.schemas import CommentUpdate
    with pytest.raises(NotFoundError):
        await update_comment(db, 20, _user(1, "member"), CommentUpdate(content="x"))


# ─── delete_comment permissions ───────────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.services.comment_service.ThreadRepository")
@patch("app.services.comment_service.CommentRepository")
async def test_owner_can_delete_comment(mock_comment_repo, mock_thread_repo):
    mock_comment_repo.get_by_id = AsyncMock(return_value=_make_comment(user_id=1))
    mock_comment_repo.soft_delete = AsyncMock()
    mock_thread_repo.increment_comment_count = AsyncMock()
    db = AsyncMock()
    await delete_comment(db, 20, _user(1, "member"))


@pytest.mark.asyncio
@patch("app.services.comment_service.ThreadRepository")
@patch("app.services.comment_service.CommentRepository")
async def test_moderator_can_delete_others_comment(mock_comment_repo, mock_thread_repo):
    mock_comment_repo.get_by_id = AsyncMock(return_value=_make_comment(user_id=1))
    mock_comment_repo.soft_delete = AsyncMock()
    mock_thread_repo.increment_comment_count = AsyncMock()
    db = AsyncMock()
    await delete_comment(db, 20, _user(99, "moderator"))


@pytest.mark.asyncio
@patch("app.services.comment_service.ThreadRepository")
@patch("app.services.comment_service.CommentRepository")
async def test_admin_can_delete_others_comment(mock_comment_repo, mock_thread_repo):
    mock_comment_repo.get_by_id = AsyncMock(return_value=_make_comment(user_id=1))
    mock_comment_repo.soft_delete = AsyncMock()
    mock_thread_repo.increment_comment_count = AsyncMock()
    db = AsyncMock()
    await delete_comment(db, 20, _user(99, "admin"))


@pytest.mark.asyncio
@patch("app.services.comment_service.CommentRepository")
async def test_member_cannot_delete_others_comment(mock_repo):
    mock_repo.get_by_id = AsyncMock(return_value=_make_comment(user_id=1))
    db = AsyncMock()
    with pytest.raises(ForbiddenError):
        await delete_comment(db, 20, _user(99, "member"))


@pytest.mark.asyncio
@patch("app.services.comment_service.CommentRepository")
async def test_cannot_delete_already_deleted_comment(mock_repo):
    mock_repo.get_by_id = AsyncMock(return_value=_make_comment(user_id=1, is_deleted=True))
    db = AsyncMock()
    with pytest.raises(ValidationError):
        await delete_comment(db, 20, _user(1, "member"))
