import re
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.comment_repository import CommentRepository
from app.repositories.thread_repository import ThreadRepository
from app.repositories.user_cache_repository import UserCacheRepository
from app.db.redis import publish_event
from app.db.schemas import CommentCreate, CommentUpdate
from app.core.dependencies import CurrentUser
from app.utils.exceptions import NotFoundError, ForbiddenError, ValidationError
from app.utils.constants import MAX_COMMENT_DEPTH, FEED_WEIGHT_COMMENT

MENTION_RE = re.compile(r'@([a-zA-Z0-9_]+)')


async def _update_affinity(db: AsyncSession, user_id: int,
                            thread_id: int, weight: float):
    """Increment user_tag_affinity for all tags on the thread."""
    from sqlalchemy.dialects.postgresql import insert
    from app.db.models import UserTagAffinity, ThreadTag
    from sqlalchemy import select
    tag_rows = await db.execute(select(ThreadTag.tag_id).where(
        ThreadTag.thread_id == thread_id))
    tag_ids = [r.tag_id for r in tag_rows]
    for tag_id in tag_ids:
        stmt = insert(UserTagAffinity).values(
            user_id=user_id, tag_id=tag_id, score=weight
        ).on_conflict_do_update(
            index_elements=['user_id', 'tag_id'],
            set_={'score': UserTagAffinity.score + weight}
        )
        await db.execute(stmt)
    await db.commit()


async def create_comment(db: AsyncSession, user: CurrentUser,
                         thread_id: int, data: CommentCreate):
    # Verify thread exists
    thread = await ThreadRepository.get_by_id(db, thread_id)
    if not thread or thread.is_deleted:
        raise NotFoundError('Thread')

    depth = 0
    parent_author_id = None

    if data.parent_id:
        parent = await CommentRepository.get_by_id(db, data.parent_id)
        if not parent:
            raise NotFoundError('Parent comment')
        if parent.thread_id != thread_id:
            raise ValidationError('Parent comment does not belong to this thread')
        depth = parent.depth + 1
        if depth > MAX_COMMENT_DEPTH:
            raise ValidationError(f'Max comment depth is {MAX_COMMENT_DEPTH}')
        parent_author_id = parent.user_id

    comment = await CommentRepository.create(
        db, thread_id, user.id, data.content, data.parent_id, depth
    )

    # Increment thread comment counter
    await ThreadRepository.increment_comment_count(db, thread_id)

    # Handle @mentions
    mentioned_usernames = set(MENTION_RE.findall(data.content))
    for username in mentioned_usernames:
        mentioned_user_results = await UserCacheRepository.search_by_prefix(
            db, username, limit=1
        )
        # Only exact match triggers notification
        exact = [u for u in mentioned_user_results if u.username == username]
        if exact:
            await publish_event(f'user:{exact[0].id}:notifs', {
                'event':      'mention',
                'actor_id':   user.id,
                'thread_id':  thread_id,
                'comment_id': comment.id,
            })

    # Notify thread owner of new top-level comment
    if not data.parent_id and thread.user_id != user.id:
        await publish_event(f'user:{thread.user_id}:notifs', {
            'event':      'comment',
            'actor_id':   user.id,
            'thread_id':  thread_id,
            'comment_id': comment.id,
        })

    # Notify parent author of reply
    if parent_author_id and parent_author_id != user.id:
        await publish_event(f'user:{parent_author_id}:notifs', {
            'event':      'reply',
            'actor_id':   user.id,
            'thread_id':  thread_id,
            'comment_id': comment.id,
        })

    # Update feed affinity
    await _update_affinity(db, user.id, thread_id, FEED_WEIGHT_COMMENT)

    # Broadcast new comment to thread subscribers
    await publish_event(f'thread:{thread_id}:comments', {
        'event': 'new_comment',
        'comment_id': comment.id,
        'author': user.username,
        'parent_id': data.parent_id,
    })

    return comment


async def delete_comment(db: AsyncSession, comment_id: int, user: CurrentUser):
    comment = await CommentRepository.get_by_id(db, comment_id)
    if not comment:
        raise NotFoundError('Comment')
    if comment.user_id != user.id and user.role not in ('admin', 'moderator'):
        raise ForbiddenError()
    if comment.is_deleted:
        raise ValidationError('Comment already deleted')
    await CommentRepository.soft_delete(db, comment_id)
    # Decrement thread counter
    await ThreadRepository.increment_comment_count(db, comment.thread_id, delta=-1)


async def update_comment(db: AsyncSession, comment_id: int,
                         user: CurrentUser, data: CommentUpdate):
    comment = await CommentRepository.get_by_id(db, comment_id)
    if not comment:
        raise NotFoundError('Comment')
    if comment.is_deleted:
        raise ValidationError('Cannot edit a deleted comment')
    if comment.user_id != user.id:
        raise ForbiddenError('You can only edit your own comments')
    await CommentRepository.update_content(db, comment_id, data.content)
