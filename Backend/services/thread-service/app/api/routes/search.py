from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.repositories.search_repository import SearchRepository
from app.repositories.user_cache_repository import UserCacheRepository
from app.utils.constants import DEFAULT_PAGE_SIZE

router = APIRouter(prefix='/search', tags=['Search'])


@router.get('/threads')
async def search_threads(
    q: str = Query(..., min_length=1),
    limit: int = Query(DEFAULT_PAGE_SIZE, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    threads, total = await SearchRepository.search_threads(db, q, limit, offset)
    return {'threads': threads, 'total': total}


@router.get('/users')
async def search_users(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Prefix search for @mention autocomplete."""
    users = await UserCacheRepository.search_by_prefix(db, q, limit)
    return [{'id': u.id, 'username': u.username} for u in users]
