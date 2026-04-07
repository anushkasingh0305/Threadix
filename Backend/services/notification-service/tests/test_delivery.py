import os
import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("JWT_ALGORITHM", "HS256")

from unittest.mock import AsyncMock, patch
from app.services.delivery import deliver_notification


@pytest.mark.asyncio
@patch("app.services.delivery.send_notification_email", new_callable=AsyncMock)
@patch("app.services.delivery.publish", new_callable=AsyncMock)
@patch("app.services.delivery.is_user_online", new_callable=AsyncMock)
async def test_online_user_gets_ws_push(mock_online, mock_publish, mock_email):
    mock_online.return_value = True
    await deliver_notification(
        recipient_id=1, recipient_email="a@b.com",
        actor_username="alice", notif_type="like",
        thread_id=10, comment_id=20, notif_id=99,
    )
    mock_publish.assert_called_once()
    channel = mock_publish.call_args[0][0]
    assert channel == "user:1:ws"
    mock_email.assert_not_called()


@pytest.mark.asyncio
@patch("app.services.delivery.send_notification_email", new_callable=AsyncMock)
@patch("app.services.delivery.publish", new_callable=AsyncMock)
@patch("app.services.delivery.is_user_online", new_callable=AsyncMock)
async def test_offline_user_gets_email(mock_online, mock_publish, mock_email):
    mock_online.return_value = False
    await deliver_notification(
        recipient_id=2, recipient_email="bob@test.com",
        actor_username="alice", notif_type="comment",
        thread_id=5, comment_id=15, notif_id=42,
    )
    mock_email.assert_called_once_with("bob@test.com", "alice", "comment", 5)
    mock_publish.assert_not_called()


@pytest.mark.asyncio
@patch("app.services.delivery.send_notification_email", new_callable=AsyncMock)
@patch("app.services.delivery.publish", new_callable=AsyncMock)
@patch("app.services.delivery.is_user_online", new_callable=AsyncMock)
async def test_ws_payload_contains_required_fields(mock_online, mock_publish, mock_email):
    mock_online.return_value = True
    await deliver_notification(
        recipient_id=3, recipient_email="c@d.com",
        actor_username="charlie", notif_type="mention",
        thread_id=7, comment_id=8, notif_id=55,
    )
    payload = mock_publish.call_args[0][1]
    assert payload["id"] == 55
    assert payload["type"] == "mention"
    assert payload["thread_id"] == 7
    assert payload["comment_id"] == 8
    assert payload["actor"] == "charlie"
