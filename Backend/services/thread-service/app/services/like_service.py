from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.like_repository import LikeRepository
from app.repositories.thread_repository import ThreadRepository
from app.db.redis import publish_event
from app.core.dependencies import CurrentUser
from app.utils.exceptions import NotFoundError
from app.utils.constants import FEED_WEIGHT_LIKE


async def toggle_thread_like(db: AsyncSession, thread_id: int,
                             user: CurrentUser) -> dict:
    thread = await ThreadRepository.get_by_id(db, thread_id)
    if not thread or thread.is_deleted:
        raise NotFoundError('Thread')

    existing = await LikeRepository.get_thread_like(db, user.id, thread_id)
    if existing:
        await LikeRepository.remove_thread_like(db, user.id, thread_id)
        liked = False
        new_count = thread.like_count - 1
    else:
        await LikeRepository.add_thread_like(db, user.id, thread_id)
        liked = True
        new_count = thread.like_count + 1
        # Update affinity on like
        from app.services.comment_service import _update_affinity
        await _update_affinity(db, user.id, thread_id, FEED_WEIGHT_LIKE)
        # Notify thread author
        if thread.user_id != user.id:
            await publish_event(f'user:{thread.user_id}:notifs', {
                'event':      'like',
                'actor_id':   user.id,
                'thread_id':  thread_id,
                'comment_id': None,
            })

    # Broadcast live like count update
    await publish_event(f'thread:{thread_id}:likes', {
        'event': 'like_update',
        'thread_id': thread_id,
        'like_count': new_count,
    })

    return {'liked': liked, 'new_count': new_count}


async def toggle_comment_like(db: AsyncSession, comment_id: int,
                              user: CurrentUser) -> dict:
    from app.repositories.comment_repository import CommentRepository
    comment = await CommentRepository.get_by_id(db, comment_id)
    if not comment or comment.is_deleted:
        raise NotFoundError('Comment')

    existing = await LikeRepository.get_comment_like(db, user.id, comment_id)
    if existing:
        await LikeRepository.remove_comment_like(db, user.id, comment_id)
        liked = False
        new_count = comment.like_count - 1
    else:
        await LikeRepository.add_comment_like(db, user.id, comment_id)
        liked = True
        new_count = comment.like_count + 1

    return {'liked': liked, 'new_count': new_count}
