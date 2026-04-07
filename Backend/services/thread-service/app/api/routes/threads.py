from fastapi import APIRouter, Depends, UploadFile, File, Form, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from app.db.database import get_db
from app.core.dependencies import get_current_user, rate_limit, CurrentUser
from app.db.schemas import ThreadCreate, ThreadUpdate
from app.services.thread_service import create_thread, get_thread, update_thread, delete_thread
from app.services.media_service import upload_media
from app.services.feed_service import get_feed
from app.repositories.thread_repository import ThreadRepository
from app.utils.constants import DEFAULT_PAGE_SIZE

router = APIRouter(prefix='/threads', tags=['Threads'])


@router.post('/', dependencies=[Depends(rate_limit('thread_create', 5))])
async def create(
    title: str = Form(...),
    description: str = Form(...),
    tag_ids: Optional[str] = Form(None),  # comma-separated IDs
    files: List[UploadFile] = File(default=[]),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    parsed_tag_ids = [int(i) for i in tag_ids.split(',') if i] if tag_ids else []
    media_urls = await upload_media(files) if files else []
    data = ThreadCreate(title=title, description=description, tag_ids=parsed_tag_ids)
    thread = await create_thread(db, user, data, media_urls)
    return thread


@router.get('/feed')
async def personalized_feed(
    limit: int = Query(DEFAULT_PAGE_SIZE, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    return await get_feed(db, user.id, limit, offset)


@router.get('/')
async def list_threads(
    limit: int = Query(DEFAULT_PAGE_SIZE, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    threads, total = await ThreadRepository.get_list(db, limit, offset)
    return {'threads': threads, 'total': total, 'limit': limit, 'offset': offset}


@router.get('/{thread_id}')
async def get_one(
    thread_id: int,
    db: AsyncSession = Depends(get_db),
    user: Optional[CurrentUser] = Depends(get_current_user),
):
    thread, user_has_liked = await get_thread(db, thread_id, user)
    return {**thread.__dict__, 'user_has_liked': user_has_liked}


@router.patch('/{thread_id}')
async def update(
    thread_id: int,
    data: ThreadUpdate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    return await update_thread(db, thread_id, user, data)


@router.delete('/{thread_id}')
async def delete(
    thread_id: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    await delete_thread(db, thread_id, user)
    return {'message': 'Thread deleted'}
