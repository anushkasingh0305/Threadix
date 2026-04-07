from redis.asyncio import from_url
from app.core.config import settings

redis = from_url(settings.REDIS_URL, decode_responses=True)


async def set_key(key: str, value: str, expire: int | None = None):
    await redis.set(key, value, ex=expire)


async def get_key(key: str) -> str | None:
    return await redis.get(key)


async def delete_key(key: str):
    await redis.delete(key)


async def publish_profile_update(user_id: int, username: str, avatar_url: str | None):
    """Publish a profile update event to a Redis stream consumed by thread-service."""
    await redis.xadd('user_profile_updates', {
        'user_id': str(user_id),
        'username': username,
        'avatar_url': avatar_url or '',
    })
