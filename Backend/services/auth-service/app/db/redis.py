from redis.asyncio import from_url
from app.core.config import settings

redis = from_url(settings.REDIS_URL, decode_responses=True)


async def set_key(key: str, value: str, expire: int | None = None):
    await redis.set(key, value, ex=expire)


async def get_key(key: str) -> str | None:
    return await redis.get(key)


async def delete_key(key: str):
    await redis.delete(key)
