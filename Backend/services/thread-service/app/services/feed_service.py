from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.thread_repository import ThreadRepository
from app.utils.constants import DEFAULT_PAGE_SIZE


async def get_feed(db: AsyncSession, user_id: int,
                   limit: int = DEFAULT_PAGE_SIZE, offset: int = 0):
    """
    Returns a personalized thread feed for the user.
    Scoring: SUM of user_tag_affinity.score for each tag on a thread.
    Falls back to newest threads when no affinity data exists.
    """
    threads, total = await ThreadRepository.get_personalized_feed(
        db, user_id, limit, offset
    )
    return {
        'threads': threads,
        'total': total,
        'limit': limit,
        'offset': offset,
    }
