from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.core.dependencies import get_current_user, CurrentUser
from app.repositories.tag_repository import TagRepository
from app.db.schemas import TagCreate
from app.utils.exceptions import ConflictError

router = APIRouter(prefix='/tags', tags=['Tags'])


@router.get('/')
async def list_tags(db: AsyncSession = Depends(get_db)):
    return await TagRepository.get_all(db)


@router.post('/')
async def create_tag(
    data: TagCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    existing = await TagRepository.get_by_name(db, data.name)
    if existing:
        raise ConflictError(f'Tag "{data.name}" already exists')
    return await TagRepository.create(db, data.name, user.id)
