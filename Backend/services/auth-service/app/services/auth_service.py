from app.repositories.user_repository import UserRepository
from app.core.hashing import hash_password, verify_password
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.db.models import User, UserRole
from app.db.redis import set_key, get_key, delete_key

import hashlib

ALLOWED_ROLES = {"admin", "moderator", "member"}


async def register_user(db, user_data):
    if await UserRepository.get_by_email(db, user_data.email):
        raise Exception("Email already exists")

    if await UserRepository.get_by_username(db, user_data.username):
        raise Exception("Username already taken")

    user = User(
        email=user_data.email,
        username=user_data.username,
        password_hash=hash_password(user_data.password),
        role=UserRole.member
    )

    return await UserRepository.create_user(db, user)


async def login_user(db, user_data):
    user = await UserRepository.get_by_email(db, user_data.email)

    if not user or user.is_deleted:
        raise Exception("User not found")

    if not verify_password(user_data.password, user.password_hash):
        raise Exception("Invalid password")

    if user.role.value not in ALLOWED_ROLES:
        raise Exception("Invalid role")

    access_token = create_access_token({
        "sub": str(user.id),
        "role": user.role.value,
        "username": user.username,
        "avatar_url": user.avatar_url,
        "email": user.email,
    })

    refresh_token = create_refresh_token({
        "sub": str(user.id)
    })

    hashed = hashlib.sha256(refresh_token.encode()).hexdigest()
    await set_key(f"refresh:{user.id}", hashed, expire=7*24*60*60)

    return access_token, refresh_token


async def refresh_tokens(refresh_token: str, db=None):
    payload = decode_token(refresh_token)
    user_id = payload.get("sub")

    stored = await get_key(f"refresh:{user_id}")

    hashed = hashlib.sha256(refresh_token.encode()).hexdigest()

    if not stored or stored != hashed:
        raise Exception("Session expired or token reuse")

    await delete_key(f"refresh:{user_id}")

    access_payload: dict = {"sub": user_id}
    if db is not None:
        user = await UserRepository.get_by_id(db, int(user_id))
        if user:
            access_payload["role"] = user.role.value
            access_payload["username"] = user.username
            access_payload["avatar_url"] = user.avatar_url
            access_payload["email"] = user.email

    new_access = create_access_token(access_payload)
    new_refresh = create_refresh_token({"sub": user_id})

    new_hashed = hashlib.sha256(new_refresh.encode()).hexdigest()
    await set_key(f"refresh:{user_id}", new_hashed, expire=7*24*60*60)

    return new_access, new_refresh


async def logout_user(user_id):
    await delete_key(f"refresh:{user_id}")