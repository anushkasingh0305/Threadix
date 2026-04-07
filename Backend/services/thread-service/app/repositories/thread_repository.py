from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, delete, and_
from sqlalchemy.orm import selectinload
from app.db.models import Thread, ThreadTag, Tag, Like, UserTagAffinity
from typing import Optional


class ThreadRepository:

    @staticmethod
    async def create(db: AsyncSession, user_id: int, title: str,
                     description: str, media_urls: list, tag_ids: list) -> Thread:
        thread = Thread(
            user_id=user_id, title=title,
            description=description, media_urls=media_urls
        )
        db.add(thread)
        await db.flush()  # get thread.id without committing
        # Attach tags
        for tag_id in tag_ids:
            db.add(ThreadTag(thread_id=thread.id, tag_id=tag_id))
        await db.commit()
        await db.refresh(thread)
        return thread

    @staticmethod
    async def get_by_id(db: AsyncSession, thread_id: int) -> Optional[Thread]:
        result = await db.execute(
            select(Thread)
            .where(Thread.id == thread_id)
            .options(selectinload(Thread.author), selectinload(Thread.tags))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def increment_view(db: AsyncSession, thread_id: int):
        """Incremental update — never read-then-write."""
        await db.execute(
            update(Thread)
            .where(Thread.id == thread_id)
            .values(view_count=Thread.view_count + 1)
        )
        await db.commit()

    @staticmethod
    async def increment_comment_count(db: AsyncSession, thread_id: int, delta: int = 1):
        await db.execute(
            update(Thread)
            .where(Thread.id == thread_id)
            .values(comment_count=Thread.comment_count + delta)
        )
        await db.commit()

    @staticmethod
    async def soft_delete(db: AsyncSession, thread_id: int):
        await db.execute(
            update(Thread).where(Thread.id == thread_id).values(is_deleted=True)
        )
        await db.commit()

    @staticmethod
    async def update(db: AsyncSession, thread_id: int,
                     title: Optional[str], description: Optional[str],
                     tag_ids: Optional[list]) -> Thread:
        values = {}
        if title is not None:       values['title'] = title
        if description is not None: values['description'] = description
        if values:
            await db.execute(
                update(Thread).where(Thread.id == thread_id).values(**values)
            )
        if tag_ids is not None:
            # Replace all tags
            await db.execute(
                delete(ThreadTag).where(ThreadTag.thread_id == thread_id)
            )
            for tag_id in tag_ids:
                db.add(ThreadTag(thread_id=thread_id, tag_id=tag_id))
        await db.commit()
        return await ThreadRepository.get_by_id(db, thread_id)

    @staticmethod
    async def get_list(db: AsyncSession, limit: int, offset: int):
        """Returns (threads, total_count) for pagination."""
        q = select(Thread).where(Thread.is_deleted == False)
        total = await db.scalar(select(func.count()).select_from(q.subquery()))
        result = await db.execute(
            q.options(selectinload(Thread.author), selectinload(Thread.tags))
            .order_by(Thread.created_at.desc())
            .limit(limit).offset(offset)
        )
        return result.scalars().all(), total

    @staticmethod
    async def get_personalized_feed(db: AsyncSession, user_id: int,
                                    limit: int, offset: int):
        """
        Scores each thread based on user's tag affinity.
        Score = SUM(affinity.score) for tags the thread has.
        Falls back to chronological for threads with no matching tags.
        """
        from sqlalchemy import text
        sql = text('''
            SELECT t.id,
                   COALESCE(SUM(uta.score), 0) AS affinity_score
            FROM threads t
            LEFT JOIN thread_tags tt ON tt.thread_id = t.id
            LEFT JOIN user_tag_affinity uta
                   ON uta.tag_id = tt.tag_id AND uta.user_id = :uid
            WHERE t.is_deleted = false
            GROUP BY t.id
            ORDER BY affinity_score DESC, t.created_at DESC
            LIMIT :lim OFFSET :off
        ''')
        rows = await db.execute(sql, {'uid': user_id, 'lim': limit, 'off': offset})
        thread_ids = [r.id for r in rows]
        # Fetch full thread objects in order
        if not thread_ids:
            return [], 0
        result = await db.execute(
            select(Thread)
            .where(Thread.id.in_(thread_ids))
            .options(selectinload(Thread.author), selectinload(Thread.tags))
        )
        thread_map = {t.id: t for t in result.scalars().all()}
        ordered = [thread_map[tid] for tid in thread_ids if tid in thread_map]
        total = await db.scalar(
            select(func.count()).where(Thread.is_deleted == False)
        )
        return ordered, total
