from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from sqlalchemy.orm import selectinload
from app.db.models import Comment
from typing import Optional

DELETED_PLACEHOLDER = '[This comment has been deleted]'


class CommentRepository:

    @staticmethod
    async def create(db: AsyncSession, thread_id: int, user_id: int,
                     content: str, parent_id: Optional[int],
                     depth: int) -> Comment:
        comment = Comment(
            thread_id=thread_id, user_id=user_id,
            content=content, parent_id=parent_id, depth=depth
        )
        db.add(comment)
        await db.commit()
        await db.refresh(comment)
        return comment

    @staticmethod
    async def get_by_id(db: AsyncSession, comment_id: int) -> Optional[Comment]:
        result = await db.execute(
            select(Comment)
            .where(Comment.id == comment_id)
            .options(selectinload(Comment.author))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_top_level(db: AsyncSession, thread_id: int,
                            limit: int, offset: int):
        """Fetches only parent_id=NULL comments (top-level)."""
        q = select(Comment).where(
            Comment.thread_id == thread_id,
            Comment.parent_id == None
        )
        total = await db.scalar(select(func.count()).select_from(q.subquery()))
        result = await db.execute(
            q.options(selectinload(Comment.author))
            .order_by(Comment.created_at.asc())
            .limit(limit).offset(offset)
        )
        return result.scalars().all(), total

    @staticmethod
    async def get_children(db: AsyncSession, parent_id: int,
                           limit: int, offset: int):
        """Load more children for a parent comment."""
        q = select(Comment).where(Comment.parent_id == parent_id)
        total = await db.scalar(select(func.count()).select_from(q.subquery()))
        result = await db.execute(
            q.options(selectinload(Comment.author))
            .order_by(Comment.created_at.asc())
            .limit(limit).offset(offset)
        )
        return result.scalars().all(), total

    @staticmethod
    async def count_children(db: AsyncSession, parent_id: int) -> int:
        return await db.scalar(
            select(func.count()).where(Comment.parent_id == parent_id)
        )

    @staticmethod
    async def soft_delete(db: AsyncSession, comment_id: int):
        """
        Soft delete: flag is_deleted=True, replace content with placeholder.
        Children are preserved. UI shows placeholder text.
        """
        await db.execute(
            update(Comment)
            .where(Comment.id == comment_id)
            .values(is_deleted=True, content=DELETED_PLACEHOLDER)
        )
        await db.commit()

    @staticmethod
    async def update_content(db: AsyncSession, comment_id: int, content: str):
        await db.execute(
            update(Comment).where(Comment.id == comment_id).values(content=content)
        )
        await db.commit()
