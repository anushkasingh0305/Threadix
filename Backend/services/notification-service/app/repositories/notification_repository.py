from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from app.db.models import Notification
from typing import Optional


class NotificationRepository:

    @staticmethod
    async def create(
        db: AsyncSession,
        recipient_id: int,
        actor_id: int,
        notif_type: str,
        thread_id: Optional[int] = None,
        comment_id: Optional[int] = None,
    ) -> Optional[Notification]:
        # Never notify yourself
        if recipient_id == actor_id:
            return None
        n = Notification(
            recipient_id=recipient_id,
            actor_id=actor_id,
            type=notif_type,
            thread_id=thread_id,
            comment_id=comment_id,
        )
        db.add(n)
        await db.commit()
        await db.refresh(n)
        return n

    @staticmethod
    async def get_for_user(
        db: AsyncSession, user_id: int, limit: int, offset: int
    ):
        from app.db.models import UserCache
        q = select(Notification).where(Notification.recipient_id == user_id)
        total = await db.scalar(select(func.count()).select_from(q.subquery()))
        unread = await db.scalar(
            select(func.count()).where(
                Notification.recipient_id == user_id,
                Notification.is_read == False
            )
        )
        result = await db.execute(
            q.order_by(Notification.created_at.desc()).limit(limit).offset(offset)
        )
        notifs = result.scalars().all()

        # Resolve actor usernames from users_cache
        enriched = []
        for n in notifs:
            actor = await db.scalar(select(UserCache).where(UserCache.id == n.actor_id))
            d = {c.name: getattr(n, c.name) for c in n.__table__.columns}
            d['actor_username'] = actor.username if actor else f'user_{n.actor_id}'
            enriched.append(d)

        return enriched, total, unread

    @staticmethod
    async def mark_read(db: AsyncSession, notif_id: int, user_id: int):
        await db.execute(
            update(Notification)
            .where(Notification.id == notif_id,
                   Notification.recipient_id == user_id)
            .values(is_read=True)
        )
        await db.commit()

    @staticmethod
    async def mark_all_read(db: AsyncSession, user_id: int):
        await db.execute(
            update(Notification)
            .where(Notification.recipient_id == user_id,
                   Notification.is_read == False)
            .values(is_read=True)
        )
        await db.commit()

    @staticmethod
    async def get_unread_count(db: AsyncSession, user_id: int) -> int:
        return await db.scalar(
            select(func.count()).where(
                Notification.recipient_id == user_id,
                Notification.is_read == False
            )
        )
