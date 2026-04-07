from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from app.db.models import UserCache
from typing import Optional


class UserCacheRepository:

    @staticmethod
    async def upsert(db: AsyncSession, user_id: int, username: str,
                     avatar_url: Optional[str], role: str) -> None:
        """
        Insert or update user cache row.
        Uses PostgreSQL ON CONFLICT DO UPDATE for atomicity.
        Called on every authenticated request via dependencies.py.
        """
        stmt = insert(UserCache).values(
            id=user_id, username=username, avatar_url=avatar_url, role=role
        ).on_conflict_do_update(
            index_elements=['id'],
            set_={'username': username, 'avatar_url': avatar_url, 'role': role}
        )
        await db.execute(stmt)
        await db.commit()

    @staticmethod
    async def search_by_prefix(db: AsyncSession, prefix: str, limit: int = 20):
        """
        Returns users whose username starts with `prefix`.
        Used for @mention dropdown suggestions.
        IMPORTANT: Uses LIKE 'prefix%' not '%prefix%' to use the index.
        """
        result = await db.execute(
            select(UserCache)
            .where(UserCache.username.ilike(f'{prefix}%'))
            .limit(limit)
        )
        return result.scalars().all()
