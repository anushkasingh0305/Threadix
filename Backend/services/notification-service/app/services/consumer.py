import asyncio
import json
import re
from app.db.redis import get_redis
from app.db.database import AsyncSessionLocal
from app.repositories.notification_repository import NotificationRepository
from app.repositories.user_cache_repository import UserCacheRepository
from app.services.delivery import deliver_notification
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

# Regex to extract user_id from channel name 'user:42:notifs'
CHANNEL_RE = re.compile(r'user:(\d+):notifs')


async def _process_event(channel: str, data: dict):
    """
    Called for each Redis pub/sub message.
    Parses the channel to get recipient_id, writes notification to DB,
    then routes delivery.
    """
    match = CHANNEL_RE.match(channel)
    if not match:
        return
    recipient_id = int(match.group(1))

    event      = data.get('event')
    actor_id   = data.get('actor_id')
    thread_id  = data.get('thread_id')
    comment_id = data.get('comment_id')

    if not event or not actor_id:
        logger.warning(f'Malformed event on {channel}: {data}')
        return

    async with AsyncSessionLocal() as db:
        notif = await NotificationRepository.create(
            db,
            recipient_id=recipient_id,
            actor_id=actor_id,
            notif_type=event,
            thread_id=thread_id,
            comment_id=comment_id,
        )
        if notif is None:
            return  # self-notification, skip

        actor     = await UserCacheRepository.get_by_id(db, actor_id)
        recipient = await UserCacheRepository.get_by_id(db, recipient_id)

    actor_username  = actor.username if actor else f'user_{actor_id}'
    recipient_email = recipient.email if recipient else ''

    await deliver_notification(
        recipient_id=recipient_id,
        recipient_email=recipient_email,
        actor_username=actor_username,
        notif_type=event,
        thread_id=thread_id or 0,
        comment_id=comment_id or 0,
        notif_id=notif.id,
    )


async def start_consumer():
    """
    Long-running task. Called once from main.py lifespan.
    Uses PSUBSCRIBE to match all user notification channels.
    Runs forever until the service shuts down.
    """
    logger.info('Notification consumer starting...')
    r = await get_redis()
    pubsub = r.pubsub()

    await pubsub.psubscribe('user:*:notifs')
    logger.info('Subscribed to pattern: user:*:notifs')

    async for message in pubsub.listen():
        if message['type'] != 'pmessage':
            continue
        try:
            channel = message['channel']
            data    = json.loads(message['data'])
            asyncio.create_task(_process_event(channel, data))
        except Exception as e:
            logger.error(f'Consumer error: {e}')
