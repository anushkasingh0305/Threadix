from sqlalchemy.future import select
from app.db.models import User

class UserRepository:

    @staticmethod
    async def get_by_email(db, email):
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_username(db, username):
        result = await db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_id(db, user_id):
        result = await db.execute(select(User).where(User.id == int(user_id)))
        return result.scalar_one_or_none()

    @staticmethod
    async def create_user(db, user):
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def update_user(db, user):
        await db.commit()
        await db.refresh(user)
        return user