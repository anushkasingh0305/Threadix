from app.core.security import decode_token
from app.repositories.user_repository import UserRepository
from app.core.hashing import hash_password


async def reset_password(db, token, new_password):
    payload = decode_token(token)
    user = await UserRepository.get_by_id(db, payload["sub"])

    user.password_hash = hash_password(new_password)

    await UserRepository.update_user(db, user)