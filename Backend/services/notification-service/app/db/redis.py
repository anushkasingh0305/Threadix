import json
import redis.asyncio as aioredis
from app.core.config import settings

_redis: aioredis.Redis = None
ONLINE_TTL = 30  # seconds — renewed by WebSocket heartbeat


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


# ─── Pub/Sub ─────────────────────────────────────────────────────────────────

async def publish(channel: str, payload: dict):
    r = await get_redis()
    await r.publish(channel, json.dumps(payload))


async def subscribe(channel: str):
    r = await get_redis()
    ps = r.pubsub()
    await ps.subscribe(channel)
    return ps


async def subscribe_many(channels: list[str]):
    r = await get_redis()
    ps = r.pubsub()
    await ps.subscribe(*channels)
    return ps


# ─── Online presence ─────────────────────────────────────────────────────────

async def set_user_online(user_id: int):
    """Called when WS connects and on every heartbeat ping."""
    r = await get_redis()
    await r.setex(f'user:{user_id}:online', ONLINE_TTL, '1')


async def set_user_offline(user_id: int):
    """Called when WS disconnects."""
    r = await get_redis()
    await r.delete(f'user:{user_id}:online')


async def is_user_online(user_id: int) -> bool:
    r = await get_redis()
    val = await r.get(f'user:{user_id}:online')
    return val is not None
