from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_
from app.db.models import Like, Thread, Comment
from typing import Optional


class LikeRepository:

    @staticmethod
    async def get_thread_like(db: AsyncSession, user_id: int,
                              thread_id: int) -> Optional[Like]:
        result = await db.execute(
            select(Like).where(
                and_(Like.user_id == user_id, Like.thread_id == thread_id)
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_comment_like(db: AsyncSession, user_id: int,
                               comment_id: int) -> Optional[Like]:
        result = await db.execute(
            select(Like).where(
                and_(Like.user_id == user_id, Like.comment_id == comment_id)
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def add_thread_like(db: AsyncSession, user_id: int, thread_id: int):
        """Add like row + increment counter atomically."""
        db.add(Like(user_id=user_id, thread_id=thread_id))
        await db.execute(
            update(Thread)
            .where(Thread.id == thread_id)
            .values(like_count=Thread.like_count + 1)
        )
        await db.commit()

    @staticmethod
    async def remove_thread_like(db: AsyncSession, user_id: int, thread_id: int):
        """Hard delete like row + decrement counter."""
        await db.execute(
            delete(Like).where(
                and_(Like.user_id == user_id, Like.thread_id == thread_id)
            )
        )
        await db.execute(
            update(Thread)
            .where(Thread.id == thread_id)
            .values(like_count=Thread.like_count - 1)
        )
        await db.commit()

    @staticmethod
    async def add_comment_like(db: AsyncSession, user_id: int, comment_id: int):
        db.add(Like(user_id=user_id, comment_id=comment_id))
        await db.execute(
            update(Comment)
            .where(Comment.id == comment_id)
            .values(like_count=Comment.like_count + 1)
        )
        await db.commit()

    @staticmethod
    async def remove_comment_like(db: AsyncSession, user_id: int, comment_id: int):
        await db.execute(
            delete(Like).where(
                and_(Like.user_id == user_id, Like.comment_id == comment_id)
            )
        )
        await db.execute(
            update(Comment)
            .where(Comment.id == comment_id)
            .values(like_count=Comment.like_count - 1)
        )
        await db.commit()
