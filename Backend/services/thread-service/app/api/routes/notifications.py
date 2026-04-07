from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.core.dependencies import get_current_user, CurrentUser
from app.repositories.notification_repository import NotificationRepository
from app.utils.constants import DEFAULT_PAGE_SIZE

router = APIRouter(prefix='/notifications', tags=['Notifications'])


@router.get('/')
async def get_notifications(
    limit: int = Query(DEFAULT_PAGE_SIZE, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    notifs, total = await NotificationRepository.get_for_user(
        db, user.id, limit, offset
    )
    return {'notifications': notifs, 'total': total}


@router.patch('/{notif_id}/read')
async def mark_read(
    notif_id: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    await NotificationRepository.mark_read(db, notif_id, user.id)
    return {'message': 'Marked as read'}
