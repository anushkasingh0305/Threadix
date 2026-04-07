from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from app.db.models import Tag
from app.utils.constants import SEEDED_TAGS
from typing import List, Optional


class TagRepository:

    @staticmethod
    async def seed(db: AsyncSession):
        """Insert seeded tags on startup. Skip if already exists."""
        for name in SEEDED_TAGS:
            stmt = insert(Tag).values(name=name, is_seeded=True).on_conflict_do_nothing()
            await db.execute(stmt)
        await db.commit()

    @staticmethod
    async def get_all(db: AsyncSession) -> List[Tag]:
        result = await db.execute(select(Tag).order_by(Tag.is_seeded.desc(), Tag.name))
        return result.scalars().all()

    @staticmethod
    async def get_by_ids(db: AsyncSession, ids: List[int]) -> List[Tag]:
        result = await db.execute(select(Tag).where(Tag.id.in_(ids)))
        return result.scalars().all()

    @staticmethod
    async def get_by_name(db: AsyncSession, name: str) -> Optional[Tag]:
        result = await db.execute(select(Tag).where(Tag.name == name))
        return result.scalar_one_or_none()

    @staticmethod
    async def create(db: AsyncSession, name: str, created_by: int) -> Tag:
        tag = Tag(name=name, is_seeded=False, created_by=created_by)
        db.add(tag)
        await db.commit()
        await db.refresh(tag)
        return tag
