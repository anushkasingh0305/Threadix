from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.core.dependencies import get_current_user, CurrentUser
from app.repositories.notification_repository import NotificationRepository

router = APIRouter(prefix='/notifications', tags=['Notifications'])


@router.get('/')
async def list_notifications(
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    notifs, total, unread = await NotificationRepository.get_for_user(
        db, user.id, limit, offset
    )
    return {
        'notifications': notifs,
        'total': total,
        'unread_count': unread,
        'limit': limit,
        'offset': offset,
    }


@router.get('/unread-count')
async def unread_count(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    count = await NotificationRepository.get_unread_count(db, user.id)
    return {'unread_count': count}


@router.patch('/{notif_id}/read')
async def mark_read(
    notif_id: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    await NotificationRepository.mark_read(db, notif_id, user.id)
    return {'message': 'Marked as read'}


@router.patch('/read-all')
async def mark_all_read(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    await NotificationRepository.mark_all_read(db, user.id)
    return {'message': 'All notifications marked as read'}
