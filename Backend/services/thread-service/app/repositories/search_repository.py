from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from app.db.models import Thread, Tag, ThreadTag


class SearchRepository:

    @staticmethod
    async def search_threads(db: AsyncSession, query: str,
                             limit: int, offset: int):
        """
        Searches thread title and description using PostgreSQL ILIKE.
        Also matches threads whose tags contain the query.
        """
        pattern = f'%{query}%'
        # Threads matching by title or description
        text_match = select(Thread.id).where(
            Thread.is_deleted == False,
            or_(
                Thread.title.ilike(pattern),
                Thread.description.ilike(pattern)
            )
        )
        # Threads matching by tag name
        tag_match = (
            select(ThreadTag.thread_id)
            .join(Tag, Tag.id == ThreadTag.tag_id)
            .where(Tag.name.ilike(pattern))
        )
        combined_ids = text_match.union(tag_match).subquery()
        q = select(Thread).where(Thread.id.in_(select(combined_ids)))
        total = await db.scalar(select(func.count()).select_from(q.subquery()))
        result = await db.execute(
            q.options(selectinload(Thread.author), selectinload(Thread.tags))
            .order_by(Thread.created_at.desc())
            .limit(limit).offset(offset)
        )
        return result.scalars().all(), total
