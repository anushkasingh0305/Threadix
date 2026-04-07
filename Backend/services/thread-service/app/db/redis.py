import json
import redis.asyncio as aioredis
from app.core.config import settings

_redis: aioredis.Redis = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


# ─── Pub/Sub helpers ─────────────────────────────────────────────────────────

async def publish_event(channel: str, payload: dict):
    """Publish a JSON event to a Redis channel."""
    r = await get_redis()
    await r.publish(channel, json.dumps(payload))


async def subscribe_to_channel(channel: str):
    """Returns a pubsub object subscribed to the given channel."""
    r = await get_redis()
    pubsub = r.pubsub()
    await pubsub.subscribe(channel)
    return pubsub


# Channel name conventions:
#   'threads'              → new thread created
#   'thread:{id}:likes'    → like count update for a thread
#   'thread:{id}:comments' → new comment on a thread
#   'user:{id}:notifs'     → notification for a specific user

# ─── Rate limiting ───────────────────────────────────────────────────────────

async def increment_rate_limit(key: str, window_seconds: int) -> int:
    """
    Increments a counter key. Sets TTL on first increment.
    Returns current count after increment.
    """
    r = await get_redis()
    pipe = r.pipeline()
    pipe.incr(key)
    pipe.expire(key, window_seconds)  # no-op if key already has TTL
    results = await pipe.execute()
    return results[0]  # the incremented count


async def get_rate_limit_count(key: str) -> int:
    r = await get_redis()
    val = await r.get(key)
    return int(val) if val else 0


# ─── Thread view caching (optional optimization) ─────────────────────────────

async def cache_thread(thread_id: int, data: dict, ttl: int = 300):
    r = await get_redis()
    await r.setex(f'thread:{thread_id}', ttl, json.dumps(data))


async def get_cached_thread(thread_id: int) -> dict | None:
    r = await get_redis()
    val = await r.get(f'thread:{thread_id}')
    return json.loads(val) if val else None


async def invalidate_thread_cache(thread_id: int):
    r = await get_redis()
    await r.delete(f'thread:{thread_id}')
