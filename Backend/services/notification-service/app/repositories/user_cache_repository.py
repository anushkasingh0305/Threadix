from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from app.db.models import UserCache
from typing import Optional


class UserCacheRepository:

    @staticmethod
    async def upsert(
        db: AsyncSession, user_id: int, username: str,
        email: str, avatar_url: Optional[str], role: str
    ) -> None:
        stmt = insert(UserCache).values(
            id=user_id, username=username, email=email,
            avatar_url=avatar_url, role=role
        ).on_conflict_do_update(
            index_elements=['id'],
            set_={'username': username, 'email': email,
                  'avatar_url': avatar_url, 'role': role}
        )
        await db.execute(stmt)
        await db.commit()

    @staticmethod
    async def get_by_id(db: AsyncSession, user_id: int) -> Optional[UserCache]:
        result = await db.execute(
            select(UserCache).where(UserCache.id == user_id)
        )
        return result.scalar_one_or_none()
