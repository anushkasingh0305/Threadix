from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.thread_repository import ThreadRepository
from app.repositories.tag_repository import TagRepository
from app.repositories.like_repository import LikeRepository
from app.db.redis import publish_event, invalidate_thread_cache
from app.utils.exceptions import NotFoundError, ForbiddenError, ValidationError
from app.db.schemas import ThreadCreate, ThreadUpdate
from app.core.dependencies import CurrentUser
from typing import Optional


async def create_thread(db: AsyncSession, user: CurrentUser,
                        data: ThreadCreate, media_urls: list) -> dict:
    # Validate tags
    if len(set(data.tag_ids)) != len(data.tag_ids):
        raise ValidationError('Duplicate tags are not allowed')
    if data.tag_ids:
        tags = await TagRepository.get_by_ids(db, data.tag_ids)
        if len(tags) != len(data.tag_ids):
            raise ValidationError('One or more tag IDs are invalid')

    thread = await ThreadRepository.create(
        db, user.id, data.title, data.description, media_urls, data.tag_ids
    )

    # Broadcast new thread to all connected WS clients
    await publish_event('threads', {
        'event': 'new_thread',
        'thread_id': thread.id,
        'title': thread.title,
        'author': user.username,
    })
    return thread


async def get_thread(db: AsyncSession, thread_id: int,
                     current_user: Optional[CurrentUser]) -> dict:
    thread = await ThreadRepository.get_by_id(db, thread_id)
    if not thread or thread.is_deleted:
        raise NotFoundError('Thread')

    # Increment view count (incremental, not snapshot)
    await ThreadRepository.increment_view(db, thread_id)
    await db.refresh(thread)

    # Check if user has liked
    user_has_liked = False
    if current_user:
        like = await LikeRepository.get_thread_like(db, current_user.id, thread_id)
        user_has_liked = like is not None

    return thread, user_has_liked


async def update_thread(db: AsyncSession, thread_id: int,
                        user: CurrentUser, data: ThreadUpdate):
    thread = await ThreadRepository.get_by_id(db, thread_id)
    if not thread or thread.is_deleted:
        raise NotFoundError('Thread')
    # Only author, moderator, admin can edit
    if thread.user_id != user.id and user.role not in ('admin', 'moderator'):
        raise ForbiddenError('You can only edit your own threads')
    # Validate tags if provided
    if data.tag_ids is not None:
        if len(set(data.tag_ids)) != len(data.tag_ids):
            raise ValidationError('Duplicate tags not allowed')
    updated = await ThreadRepository.update(
        db, thread_id, data.title, data.description, data.tag_ids
    )
    await invalidate_thread_cache(thread_id)
    return updated


async def delete_thread(db: AsyncSession, thread_id: int, user: CurrentUser):
    thread = await ThreadRepository.get_by_id(db, thread_id)
    if not thread or thread.is_deleted:
        raise NotFoundError('Thread')
    # Permission: own post OR moderator OR admin
    if thread.user_id != user.id and user.role not in ('admin', 'moderator'):
        raise ForbiddenError()
    await ThreadRepository.soft_delete(db, thread_id)
    await invalidate_thread_cache(thread_id)
