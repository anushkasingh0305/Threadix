from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.core.dependencies import get_current_user, rate_limit, CurrentUser
from app.db.schemas import CommentCreate, CommentUpdate
from app.services.comment_service import create_comment, delete_comment, update_comment
from app.repositories.comment_repository import CommentRepository
from app.utils.constants import DEFAULT_PAGE_SIZE

router = APIRouter(prefix='/threads/{thread_id}/comments', tags=['Comments'])


@router.post('/', dependencies=[Depends(rate_limit('comment_create', 20))])
async def post_comment(
    thread_id: int,
    data: CommentCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    return await create_comment(db, user, thread_id, data)


@router.get('/')
async def get_top_level_comments(
    thread_id: int,
    limit: int = Query(DEFAULT_PAGE_SIZE, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Returns only top-level (parent_id=null) comments with child_count."""
    comments, total = await CommentRepository.get_top_level(db, thread_id, limit, offset)
    result = []
    for c in comments:
        child_count = await CommentRepository.count_children(db, c.id)
        result.append({**c.__dict__, 'child_count': child_count})
    return {'comments': result, 'total': total, 'limit': limit, 'offset': offset}


@router.get('/{comment_id}/children')
async def load_more_children(
    thread_id: int,
    comment_id: int,
    limit: int = Query(5, le=50),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Load more child comments under a parent. Triggered by 'Load more' button."""
    children, total = await CommentRepository.get_children(db, comment_id, limit, offset)
    return {'comments': children, 'total': total, 'limit': limit, 'offset': offset}


@router.patch('/{comment_id}')
async def edit_comment(
    thread_id: int,
    comment_id: int,
    data: CommentUpdate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    return await update_comment(db, comment_id, user, data)


@router.delete('/{comment_id}')
async def remove_comment(
    thread_id: int,
    comment_id: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    await delete_comment(db, comment_id, user)
    return {'message': 'Comment deleted'}
