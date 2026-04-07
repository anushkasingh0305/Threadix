from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from sqlalchemy.orm import selectinload
from app.db.models import Notification
from typing import List


class NotificationRepository:

    @staticmethod
    async def create(db: AsyncSession, recipient_id: int, actor_id: int,
                     notif_type: str, thread_id=None, comment_id=None) -> Notification:
        # Skip creating if recipient == actor
        if recipient_id == actor_id:
            return None
        n = Notification(
            recipient_id=recipient_id, actor_id=actor_id,
            type=notif_type, thread_id=thread_id, comment_id=comment_id
        )
        db.add(n)
        await db.commit()
        await db.refresh(n)
        return n

    @staticmethod
    async def get_for_user(db: AsyncSession, user_id: int,
                           limit: int, offset: int):
        q = select(Notification).where(Notification.recipient_id == user_id)
        total = await db.scalar(select(func.count()).select_from(q.subquery()))
        result = await db.execute(
            q.options(selectinload(Notification.actor))
            .order_by(Notification.created_at.desc())
            .limit(limit).offset(offset)
        )
        return result.scalars().all(), total

    @staticmethod
    async def mark_read(db: AsyncSession, notif_id: int, user_id: int):
        await db.execute(
            update(Notification)
            .where(Notification.id == notif_id,
                   Notification.recipient_id == user_id)
            .values(is_read=True)
        )
        await db.commit()
