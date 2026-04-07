from fastapi import Depends, Cookie, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError
from app.core.security import decode_token
from app.db.database import get_db
from app.repositories.user_cache_repository import UserCacheRepository
from app.utils.exceptions import ForbiddenError, RateLimitError
from app.db.redis import get_rate_limit_count, increment_rate_limit
from dataclasses import dataclass
from typing import Optional


@dataclass
class CurrentUser:
    id: int
    username: str
    avatar_url: Optional[str]
    role: str


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    access_token: Optional[str] = Cookie(default=None),
) -> CurrentUser:
    if not access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail='Not authenticated')
    try:
        payload = decode_token(access_token)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail='Invalid or expired token')

    user_id  = int(payload['sub'])
    username = payload['username']
    avatar   = payload.get('avatar_url')
    role     = payload.get('role', 'member')

    # Keep users_cache up to date with latest JWT claims
    await UserCacheRepository.upsert(db, user_id, username, avatar, role)

    return CurrentUser(id=user_id, username=username, avatar_url=avatar, role=role)


def require_role(*roles: str):
    """Returns a dependency that enforces role membership."""
    async def _check(current_user: CurrentUser = Depends(get_current_user)):
        if current_user.role not in roles:
            raise ForbiddenError()
        return current_user
    return _check


def rate_limit(key_prefix: str, limit: int, window_seconds: int = 60):
    """
    Sliding window rate limiter backed by Redis.
    key_prefix: e.g. 'thread_create', 'comment_create'
    limit: max requests per window
    window_seconds: window size in seconds
    """
    async def _check(current_user: CurrentUser = Depends(get_current_user)):
        key = f'rl:{key_prefix}:{current_user.id}'
        count = await increment_rate_limit(key, window_seconds)
        if count > limit:
            raise RateLimitError()
        return current_user
    return _check
