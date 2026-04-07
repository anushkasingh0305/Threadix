from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.db.models import UserRole
from app.services.user_service import update_user_profile, change_user_password, get_user_by_username, get_user_profile
from app.repositories.user_repository import UserRepository
from app.db.schemas import ChangePassword, UserProfile

router = APIRouter()

@router.put("/profile")
async def update_profile(
    username: str | None = Form(None),
    bio: str | None = Form(None),
    file: UploadFile = File(None),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    try:
        user = await update_user_profile(db, user_id, username, bio, file)
        return {"message": "Profile updated"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/profile", response_model=UserProfile)
async def get_my_profile(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    try:
        user = await get_user_profile(db, user_id)
        return UserProfile(
            id=user.id,
            email=user.email,
            username=user.username,
            role=user.role.value,
            avatar_url=user.avatar_url,
            bio=user.bio,
            created_at=str(user.created_at)
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{username}", response_model=UserProfile)
async def get_by_username(
    username: str,
    db: AsyncSession = Depends(get_db)
):
    try:
        user = await get_user_by_username(db, username)
        return UserProfile(
            id=user.id,
            email=user.email,
            username=user.username,
            role=user.role.value,
            avatar_url=user.avatar_url,
            bio=user.bio,
            created_at=str(user.created_at)
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/change-password")
async def change_password(
    data: ChangePassword,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    try:
        await change_user_password(db, user_id, data)
        return {"message": "Password updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/role/{username}")
async def set_user_role(
    username: str,
    role: UserRole,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_role(["admin"]))
):
    user = await UserRepository.get_by_username(db, username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.role = role
    await db.commit()
    return {"message": f"{username} is now {role.value}"}


# ─── Admin endpoints ──────────────────────────────────────────────────────────

@router.get("/list")
async def list_users(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_role(["admin"]))
):
    from sqlalchemy import select, func
    from app.db.models import User
    total = await db.scalar(select(func.count()).select_from(User).where(User.is_deleted == False))
    result = await db.execute(
        select(User).where(User.is_deleted == False)
        .order_by(User.created_at.desc()).limit(limit).offset(offset)
    )
    users = result.scalars().all()
    return {
        "total": total,
        "users": [
            {"id": u.id, "username": u.username, "email": u.email,
             "role": u.role.value, "created_at": str(u.created_at)}
            for u in users
        ]
    }


@router.patch("/{user_id}/role")
async def patch_user_role(
    user_id: int,
    body: dict,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_role(["admin"]))
):
    from app.db.models import User
    from sqlalchemy import select
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        user.role = UserRole(body.get("role"))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid role")
    await db.commit()
    return {"message": f"Role updated to {user.role.value}"}


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_role(["admin"]))
):
    from app.db.models import User
    from sqlalchemy import select
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_deleted = True
    await db.commit()
    return {"message": "User deleted"}

