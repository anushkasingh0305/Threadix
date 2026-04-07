from fastapi import Depends, Cookie, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError
from typing import Optional
from dataclasses import dataclass
from app.core.security import decode_token
from app.db.database import get_db
from app.repositories.user_cache_repository import UserCacheRepository


@dataclass
class CurrentUser:
    id: int
    username: str
    email: str
    avatar_url: Optional[str]
    role: str


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    access_token: Optional[str] = Cookie(default=None),
) -> CurrentUser:
    if not access_token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Not authenticated')
    try:
        payload = decode_token(access_token)
    except JWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Invalid or expired token')

    user_id  = int(payload['sub'])
    username = payload['username']
    email    = payload.get('email', '')
    avatar   = payload.get('avatar_url')
    role     = payload.get('role', 'member')

    await UserCacheRepository.upsert(db, user_id, username, email, avatar, role)

    return CurrentUser(id=user_id, username=username, email=email,
                       avatar_url=avatar, role=role)
