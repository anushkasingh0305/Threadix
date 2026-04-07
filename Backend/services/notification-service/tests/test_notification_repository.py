import os
import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("JWT_ALGORITHM", "HS256")

from unittest.mock import AsyncMock, patch, MagicMock
from app.repositories.notification_repository import NotificationRepository


@pytest.mark.asyncio
async def test_self_notification_returns_none():
    """You should never receive a notification from yourself."""
    db = AsyncMock()
    result = await NotificationRepository.create(
        db, recipient_id=5, actor_id=5, notif_type="like",
        thread_id=1, comment_id=None,
    )
    assert result is None
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_create_notification_normal():
    """Normal notification (different users) should call db.add + db.commit."""
    db = AsyncMock()
    db.refresh = AsyncMock()
    result = await NotificationRepository.create(
        db, recipient_id=1, actor_id=2, notif_type="comment",
        thread_id=10, comment_id=20,
    )
    db.add.assert_called_once()
    db.commit.assert_called_once()
    db.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_mark_read():
    db = AsyncMock()
    await NotificationRepository.mark_read(db, notif_id=7, user_id=3)
    db.execute.assert_called_once()
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_mark_all_read():
    db = AsyncMock()
    await NotificationRepository.mark_all_read(db, user_id=3)
    db.execute.assert_called_once()
    db.commit.assert_called_once()
