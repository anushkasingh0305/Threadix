from app.db.redis import is_user_online, publish
from app.services.email_service import send_notification_email
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


async def deliver_notification(
    recipient_id: int,
    recipient_email: str,
    actor_username: str,
    notif_type: str,
    thread_id: int,
    comment_id: int,
    notif_id: int,
):
    """
    Routes a notification to the user.
    If online  → push via WebSocket (Redis pub/sub to user:{id}:ws channel).
    If offline → email delivery (not yet implemented — logs and skips).
    """
    payload = {
        'id': notif_id,
        'type': notif_type,
        'thread_id': thread_id,
        'comment_id': comment_id,
        'actor': actor_username,
    }

    online = await is_user_online(recipient_id)
    if online:
        await publish(f'user:{recipient_id}:ws', payload)
        logger.info(f'WS delivery → user {recipient_id} [{notif_type}]')
    else:
        await send_notification_email(
            recipient_email, actor_username, notif_type, thread_id
        )
        logger.info(f'Email delivery → user {recipient_id} [{notif_type}]')
