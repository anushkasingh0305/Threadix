from sqlalchemy.future import select
from app.db.models import User
from app.core.hashing import verify_password, hash_password
import cloudinary.uploader

async def update_user_profile(db, user_id, username=None, bio=None, file=None):
    result = await db.execute(
        select(User).where(User.id == int(user_id))
    )
    user = result.scalar_one_or_none()

    if not user:
        raise Exception("User not found")

    # update username if provided
    if username:
        result = await db.execute(
            select(User).where(User.username == username)
        )
        existing = result.scalar_one_or_none()
        if existing and existing.id != int(user_id):
            raise Exception("Username already taken")
        user.username = username

    # update bio if provided (empty string clears it)
    if bio is not None:
        user.bio = bio

    # upload avatar
    if file:
        if not file.content_type.startswith("image/"):
            raise Exception("Only image files allowed")
        try:
            upload = cloudinary.uploader.upload(
                file.file,
                public_id=f'threadix/avatars/user_{user_id}',
                overwrite=True,
                invalidate=True,
            )
            user.avatar_url = upload["secure_url"]
        except Exception:
            raise Exception("Avatar upload failed")

    await db.commit()
    await db.refresh(user)
    return user


async def change_user_password(db, user_id, data):
    result = await db.execute(
        select(User).where(User.id == int(user_id))
    )
    user = result.scalar_one_or_none()

    if not user:
        raise Exception("User not found")

    if not verify_password(data.current_password, user.password_hash):
        raise Exception("Current password is incorrect")

    user.password_hash = hash_password(data.new_password)
    await db.commit()
    return user


async def get_user_by_username(db, username: str):
    result = await db.execute(
        select(User).where(User.username == username, User.is_deleted == False)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise Exception("User not found")
    return user


async def get_user_profile(db, user_id):
    result = await db.execute(
        select(User).where(User.id == int(user_id), User.is_deleted == False)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise Exception("User not found")
    return user