from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.core.dependencies import get_current_user, rate_limit, CurrentUser
from app.services.like_service import toggle_thread_like, toggle_comment_like

router = APIRouter(prefix='/threads', tags=['Likes'])


@router.post('/{thread_id}/like',
             dependencies=[Depends(rate_limit('like', 60))])
async def toggle_like(
    thread_id: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    return await toggle_thread_like(db, thread_id, user)


@router.post('/{thread_id}/comments/{comment_id}/like',
             dependencies=[Depends(rate_limit('like', 60))])
async def toggle_comment_like_route(
    thread_id: int,
    comment_id: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    return await toggle_comment_like(db, comment_id, user)
