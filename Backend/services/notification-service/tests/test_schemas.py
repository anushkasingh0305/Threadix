import os
import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("JWT_ALGORITHM", "HS256")

from app.db.schemas import NotificationOut, NotificationListOut
from datetime import datetime


def test_notification_out_valid():
    n = NotificationOut(
        id=1, type="like", is_read=False,
        thread_id=10, comment_id=None,
        created_at=datetime(2026, 1, 1), actor_id=5,
    )
    assert n.type == "like"
    assert n.is_read is False
    assert n.thread_id == 10
    assert n.comment_id is None


def test_notification_out_all_types():
    for t in ("reply", "mention", "like", "comment"):
        n = NotificationOut(
            id=1, type=t, is_read=False,
            thread_id=1, comment_id=1,
            created_at=datetime(2026, 1, 1), actor_id=2,
        )
        assert n.type == t


def test_notification_list_out():
    nl = NotificationListOut(
        notifications=[], total=0, unread_count=0, limit=20, offset=0,
    )
    assert nl.total == 0
    assert nl.limit == 20


def test_notification_list_out_with_items():
    item = NotificationOut(
        id=1, type="reply", is_read=True,
        thread_id=5, comment_id=3,
        created_at=datetime(2026, 4, 7), actor_id=10,
    )
    nl = NotificationListOut(
        notifications=[item], total=1, unread_count=0, limit=20, offset=0,
    )
    assert nl.total == 1
    assert len(nl.notifications) == 1
    assert nl.notifications[0].is_read is True
